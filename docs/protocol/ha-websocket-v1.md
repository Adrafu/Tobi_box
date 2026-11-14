# WebSocket- und Upload-Schnittstelle Seite ↔ HA-Backend, Version 1 (`ha-websocket-v1`, „Vertrag W“)

*   **Status:** Vertrag Stufe 3a, überarbeitet am 09.11. nach dem Goldfisch-Report
    (`docs/egm/software-prototyp/review_vertrag_w.md`, Befunde W-01 bis W-28 mit
    „Auflösung“ am Ende des Reports), mit Entscheidung M (Einsortieren nach Metadaten)
    und den Vorgaben der Projektleitung vom 09.11. (Abschnitt „Vorgaben der
    Projektleitung“ am Ende). Wartet auf die Freigabe durch Tobias. **Stand der Rechte, des Uploads und der
    neuen Befehle: Änderungen 12.11. und 13.11. unten.**
*   **Änderung 14.11. (AC1, Tobias freigegeben; `docs/egm/ha-ui/vorschlag_sammelordner.md`): Sammelordner – Teil = Unterordner der ersten Ebene, CD/Disc-Ausnahme.**
    Neuer Begriff **Teil** (11.3): In einem Ordner-Eintrag ist jeder Unterordner der ersten Ebene ein Teil; Dateien direkt im Eintrag gehören zum Teil „Eintrag selbst“.
    Ein Unterordner, dessen Name nur eine CD- oder Disc-Angabe ist (`CD1`, `CD 2`, `Disc 1`, `Disk 2`, Groß/klein egal), ist kein eigener Teil, sondern gehört zum übergeordneten
    Teil. Gruppen werden je (Eintrag, Teil, `norm(album)`) gebildet; Dateien ohne `album` bilden **je Teil** eine Gruppe, Anzeigename und Serie aus dem Ordner sind der Name des Teils
    (11.3, 11.4, 11.5 Nr. 5). Dadurch hält eine kaputte Datei (11.10, unverändert) nur noch **ihr Buch** zurück; der Rest eines Sammelordners wird einsortiert (Status `teilweise`).
    Neuer Testfall T21 (11.12). Verhaltensänderung des Backends, kein neues Feld, keine neue Fähigkeit, Version bleibt 1: Ein Hörspiel mit Unterordnern je Folge und gleichem Album-Tag
    wird künftig zu **mehreren** Folgen. Upload (Gruppen aus `gruppe`), lose Dateien, Box, `mqtt-v1.md` und `data-model.md` ändern sich nicht.
*   **Änderung 13.11. K8 (Freigabe Tobias, 13.11.; `docs/egm/ha-ui/resolve.md`, Zeile „K8“):** Zwei additive Felder, Version bleibt 1, keine neue Fähigkeit.
    **`folgen/list`** (Nr. 37) liefert je Zeile `cover_stand` (Cover-Stand des Eintrags, **dieselbe Quelle und Form wie `cover_stand` der Serie-Kurzform**, 14.2; `null` ohne Cover)
    und `dauer_s` (Dauer der Folge in Sekunden, `number` oder `null`). **`zuordnung/list`** (Nr. 15) liefert je Zuordnung `cover_stand` des Ziels (Serie bzw. Serie der Folge;
    `null` bei Gute Nacht, Aktion, fehlender Serie oder ohne Cover). **Stand des Backends:** `dauer_s` ist vorerst immer `null`, weil HA keine Dauern speichert
    (Dauern kennt nur der Einsortier-Lauf, kurz, für die Art; sie kommen mit Stufe A-2). Die Seite behandelt `null` als „unbekannt“. Die Felder stehen **immer** da; ein älteres Backend
    lässt sie weg. Das Cover selbst holt die Seite wie bisher über die HTTP-Adresse (14.6) mit `cover_stand` als Versionsmarke. `mqtt-v1.md`, `data-model.md` und die Box ändern sich nicht.
*   **Änderung 13.11. K6/K7 (Freigabe Tobias, 13.11.; `docs/egm/ha-ui/resolve.md`, Zeile „K6/K7“):** Zwei kleine Ergänzungen, **alles additiv**, Version
    bleibt 1, keine neue Fähigkeit (die Seite erkennt K6 am Feld `vorher`, das jede Zuordnung in `zuordnung/list` trägt). **K6:** `zuordnung/list` liefert je Zuordnung
    das Feld `vorher` (`{"ziel", "am"}` oder `null`): das Ziel vor der letzten Umstellung und deren Zeitpunkt (3.5, Nr. 15 und 16), damit „Vorher: …
    · Zurückstellen“ (Design 5.4, R17-3) auf jedem Gerät steht. Es liegt **nur im HA-Speicher** (`vorher`, neben der Warteschlange), nicht in der Konfiguration:
    nicht auf `tobibox/config`, nicht im Export, nicht in `config.json`; die Box und `mqtt-v1.md`, `data-model.md` ändern sich nicht. **K7:** `warteschlange/set`
    (Nr. 47) nimmt optional `name`; beim automatischen Zuordnen wird er der Name des Tobies (3.13, Regel 7b); die Vormerkung (3.13), `warteschlange/list` (Nr. 48)
    und die Ereignisse `angelegt` und `abgearbeitet` (4.8) tragen `name` (`string` oder `null`). Ein älteres Backend lehnt die unbekannte Eingabe `name` ab: die Seite sendet sie nur, wenn sie
    nicht leer ist.
*   **Änderung 13.11. (A0-Q: Warteschlange „nächster neuer Tobie“ und Lernmodus nur für Administratoren; Freigabe Tobias 13.11.):**
    Grundlage `docs/designs/ha-oberflaeche.md` (5.13, 7.1, 10.2, 15) und `docs/egm/ha-ui/resolve.md` (X13, X13a, X20, Runde 16).
    Die Version bleibt 1 (`v` = 1), kein Versionszähler, kein neuer Wurzelname (Abschnitt 9). `mqtt-v1.md`, `data-model.md` und die Box
    ändern sich **nicht**: HA nutzt die vorhandene Meldung `…/unknown/<uid>` mit `art="unbekannt"`. **Neu und additiv:**
    3 Befehle (Nr. 47 bis 49, 3.13), das Ereignisthema `warteschlange` (4.8), die Regeln für den Abgleich beim Auflegen (3.13), die
    optionale Eingabe `als_neu` bei `zuordnung/remove` (3.5), 2 Fehlercodes `warteschlange_voll` und `warteschlange_doppelt` (Abschnitt 7),
    2 Fähigkeiten `warteschlange` und `zuordnung_rueckgaengig` (14.1), 2 Konstanten und das Feld `hello.grenzen.warteschlange_max` (14.10).
    **Ausdrücklich nicht additiv (wie am 12.11. mit Version 1 und ausdrücklicher Ausnahme):** (1) **`lernmodus/start`, `lernmodus/antwort` und
    `lernmodus/abbrechen` (Nr. 18 bis 20) sind wieder `admin`** (Entscheidung X13a, Runde 16; Design, Frage 31). Seit dem 12.11. waren sie
    `alltag`; ein Nicht-Administrator bekommt jetzt `unauthorized` (bisher Erfolg). Die Aufzählung „… 16 bis 20 …“ im Eintrag vom 12.11. gilt für
    18 bis 20 nicht mehr. HA-Aktionen und `ui/*` ändern sich nicht (die Aktionen waren schon admin). (2) **Verhaltensänderung des Backends:**
    HA ordnet erstmals **von sich aus** zu. Meldet eine Box einen unbekannten Tobie und wartet ein passender Eintrag, schreibt HA die Zuordnung
    ohne weiteren Befehl der Seite (3.13). Ohne Eintrag in der Warteschlange ändert sich nichts.
*   **Änderung 12.11. (HA-Oberfläche, Stufe A; Entwurf aus Paket A0, wartet auf die Freigabe durch Tobias):**
    Grundlage `docs/designs/ha-oberflaeche.md` (Abschnitte 10, 11, 15, 18) und `docs/egm/ha-ui/resolve.md`
    (Runden 1 bis 11). Die Version bleibt 1 (`v` = 1), es gibt keinen Versionszähler und keinen neuen Wurzelnamen
    (Abschnitt 9; Befund U18). **Alles ist additiv, mit diesen ausdrücklich nicht additiven Ausnahmen:**
    (1) **Abschnitt 2.1 ist ersetzt:** Rechte dreistufig (`lesen`, `alltag`, `admin`). Das Verhalten bestehender
    Befehle ändert sich: 15 Befehle (Nr. 6, 8, 9, 14, 16 bis 20, 24, 25, 26, 28, 30 und 36, die Admin-Teile ausgenommen) und der
    Upload waren bisher nur für Administratoren und sind jetzt für jeden angemeldeten HA-Nutzer erlaubt (bisher
    `unauthorized`, jetzt Erfolg). (2) **Verschärft:** `konfig/export_lesen` (Nr. 31) und das Feld `ereignisse` von
    `boxen/list` (Nr. 21) waren für alle lesbar und sind jetzt nur noch für Administratoren. (3) **W-19 entfällt**
    (Upload nur für Administratoren); der Prüfabschnitt „gegen die Home-Assistant-API“ nennt dafür
    `async_register_admin_service`. (4) **Neue Pflicht nur für Nicht-Administratoren:** `erwartet_ziel` bei
    `zuordnung/remove` und bei `zuordnung/set` mit `ueberschreiben=true`; `sofort`, `lesezeichen_tage` und
    die Überraschungs-Serie als Ziel nur für Administratoren (2.4). `leise_zeiten.zeitzone` wird in
    `einstellungen/set` ignoriert statt gespeichert. (5) **Upload-Grenze 2 GiB** statt 500 MiB, Reserve 2 GiB statt
    100 MiB, 16 GiB je Stunde und Benutzer (Abschnitt 8, 14.10); ein bestehender Konfigurationseintrag mit 500 MiB
    wird angehoben. (6) **`stand`** einer Serie rechnet nur noch über `name`, `folgen` und die von Menschen
    gesetzten Felder von `folgen_info` (`anzeige`, `nummer`, `datum`, `pruefen`); Werte aus Hintergrundläufen
    ändern ihn nie (Serie-Kurzform, 14.2). (7) `name` im Upload wird bis 400 Bytes gelesen (5.1). Neu sind: 10 Befehle
    (Nr. 37 bis 46, 3.12), Cover- und Audio-Ansicht (HTTP, 14.3, 14.5), Upload-Felder `ziel`, `art`, `name`,
    `gruppe_anzahl` (14.4), neue Felder in `serien/list`, `serie/get`, `eingang/list`, `boxen/list`, `zuordnung/list`,
    `papierkorb/list` und `hello`, 6 Fähigkeiten, 8 Fehlercodes (Abschnitt 7), 16 neue optionale Eingabefelder bei
    6 bestehenden Befehlen bzw. dem Upload, die Datenmodell-Ergänzungen in `data-model.md` (Store `tobibox.medieninfo`, Cover,
    `hoerkopien/`) und die Konstanten in 14.10 (Hörkopie-Grenzen **vorläufig, nach Messung A0b**).
    Stufe B (Gehört) und Stufe C (Playlists): geplant, siehe Design Abschnitte 12 und 13; nicht Teil dieses Vertrags.
    *   **Klarstellungen K1–K5 (12.11., Freigabe Tobias):**
        *   K1: `serien/list` ohne `limit` liefert alle Einträge (bisheriges Verhalten); der Zusatz „höchstens 200“ entfällt (14.2).
        *   K2: Eine Funktion `cover_pruefen_und_skalieren` mit zwei Modi, `streng` (Foto-Upload) und `nachsichtig` (Tag-Bilder, mitgelieferte Dateien) (14.3, 14.10).
        *   K3: Cover-ETag in Anführungszeichen, Antwort von POST und DELETE `{v, serie_id, cover_stand, cover_quelle}`, DELETE ohne eigenes Cover ist kein Fehler, Tag-Suche höchstens 5 Dateien je Eintrag (14.3).
        *   K4: Die Reihenfolge der Liste `hello.faehigkeiten` hat keine Bedeutung (Abschnitt 3).
        *   K5: Hörkopie-Zeitgrenze 90 Minuten je Datei, nach Messung A0b (14.10).
*   **Änderung 10.11. (Ein/Aus, 10.11.; Klarstellung):** In `tobibox/box/sync` (Abschnitt 22) heißt „Lader“ jetzt **Strom am Eingang aus jeder
    Quelle** (Netzteil, Sockel, Kabel, Powerbank). Kein neuer Befehl, kein neues Feld, Version bleibt 1.
*   **Änderung 09.11. (Entscheidung N, 09.11.):** Das Feld `lesezeichen_tage` der Konfiguration
    (Lesezeichen laufen nach so vielen Tagen ohne Benutzung ab, Vorgabe 14, `0` = nie;
    `data-model.md`, Abschnitt 2) ist **reserviert**: Das Backend schreibt es unverändert fort und
    exportiert es; die Einstellungen in Stufe 4 (`tobibox/einstellungen/get` und `set`, Abschnitt 10)
    bekommen es dazu. Eine eigene Seitenbedienung gibt es in Version 1 nicht; kein neuer Befehl,
    kein neuer Fehlercode, Version bleibt 1.
*   **Änderung 09.11. (AP 4.7, Auftrag der Projektleitung):** Die Einstellungen der Stufe 4 und die
    „Erweiterungen v1.1“ aus Abschnitt 10 gelten jetzt. Neu sind die Befehle 33 bis 36
    (`eingang/entfernen`, `konfig/get`, `einstellungen/get`, `einstellungen/set`; Abschnitte 3.9 bis 3.11),
    der optionale Filter `uid` bei `zuordnung/list`, die Felder `datei` und `pruefung` im Ereignis
    `upload`/`fortschritt` mit `zustand="fertig"` (4.7), die Fehlercodes `einstellung_ungueltig` und
    `sortierung_laeuft` (Abschnitt 7), fünf neue Werte in `hello.faehigkeiten` und die Festlegungen 25 bis 27.
    Alles **nur additiv** nach Abschnitt 9 (Version 1 bleibt, kein neuer Wurzelname). Dazu eine Klarstellung
    in Abschnitt 12, Regel 4 (Serien-Ordner `.` und `..`).
*   **Grundlage:** `docs/designs/box-software.md` (Baustein 4 „Speicher und
    Medien“, „Aktionen und Seite“, „MQTT-Schnittstelle Box ↔ HA“; D1, D2, D4,
    D5, D6; Entscheidungen D, F, H, M; CUJ 7a, 7b, 9, 10, 11, 12; AP 3.1, AP 3.2,
    AP 4.7)
*   **Gilt für:** `websocket_api.py`, `http.py`, `media.py`, `eingang.py`,
    `store.py`, `mqtt.py` der HA-Integration `tobibox` (AP 3.1) und die Seite
    `frontend/tobibox-panel.js` samt Mock (AP 3.2). Beide Seiten entstehen
    parallel und nur nach diesem Vertrag.
*   **Verwandte Verträge:** `mqtt-v1.md` (Box ↔ HA), `data-model.md`
    (`config.json`, `serie.json`, `unknown.json`, Papierkorb-Eintrag, Eingang),
    `reader-v1.md` (Format der Kennung). Auf Anweisung der Projektleitung wurden am
    09.11. **nur additiv** ergänzt: `data-model.md` (Tobie-Namen `name`,
    `serie.json` mit `folgen_info`, Papierkorb-Metadaten `meta.json`, Eingang und
    reservierte Namen) und `mqtt-v1.md` (`name` im Beispiel von `tobibox/config`).
    Wo dieser Vertrag mehr braucht, steht es unter „Offene Punkte für Tobias“.
*   **Änderung 09.11.:** Neue Befehle 24 bis 32 und Abschnitte 11 bis 13
    (Einsortieren, Namen, Zustand der Konfiguration); Upload geht in den Eingang
    (Abschnitt 5); Ereignisthema `eingang`; Papierkorb mit Serien und Metadaten;
    alle Befunde W-01 bis W-28 eingearbeitet.

Dieses Dokument ist der **einzige Vertrag** zwischen Seite und HA-Backend. Wo es
etwas nicht sagt, gilt: nicht erfinden, sondern die Projektleitung fragen.

## 1. Grundsätze

*   **Zwei Wege.** Alles außer dem Hochladen läuft über die HA-WebSocket-Schnittstelle
    (`/api/websocket`, HA-Anmeldung durch die Verbindung der HA-Oberfläche). Das
    Hochladen der Audiodateien läuft über **einen HTTP-Endpunkt** (Abschnitt 5),
    weil WebSocket-Nachrichten klein sind (Abschnitt 8).
*   **Das Backend ist der einzige Schreiber** für Zuordnungen und
    `serie.json` (D1, D2). Die Seite hält keinen eigenen Zustand, der nicht
    wieder aus den Befehlen lesbar ist (außer Ansichtseinstellungen).
*   **MQTT bleibt Verteilkanal.** Befehle, die die Konfiguration ändern, gehen in
    dieser Reihenfolge (W-06): (1) im HA-Speicher speichern (Revision + 1),
    (2) `tobibox/config` **veröffentlichen**, (3) den **Export** auf das NAS
    (`tobibox/export/`) im Hintergrund schreiben, mit Wiederholung. Das NAS kann
    also die Verteilung nie aufhalten (die Box wartet nach Entscheidung H nur 10 s
    auf die Konfiguration). Ist der Broker gerade nicht erreichbar, ist die Änderung
    trotzdem gespeichert; die Veröffentlichung wird beim Wiederverbinden nachgeholt
    (Antwortfeld `veroeffentlicht`). Ein Fehler beim Export bricht nie einen Befehl
    ab, wird aber **gemeldet** (`konfig.export_ok`, Ereignis `konfig`; Abschnitt 13).
    Solange `konfig.zustand` nicht `ok` ist, ändert kein Befehl die Konfiguration
    und die Integration veröffentlicht nichts (Abschnitt 13; ausgenommen die beiden Auswege `liste/neu_ausrollen` und `konfig/aus_export`).
*   **Medien gehen nicht über MQTT.** Befehle, die Serien, Folgen, Papierkorb oder
    den Eingang ändern, schreiben auf die NAS-Freigabe. Die Boxen holen sie mit dem
    nächsten Sync (CUJ 9); wer es eilig hat, stößt ihn mit `tobibox/box/sync` an.
    **Nicht gesynct** werden `medien/_upload/`, `medien/_papierkorb/` und der Eingang
    `tobibox/eingang/` (Entscheidung M, Abschnitt 11.1).
*   **Ein Schreibvorgang nach dem anderen.** Das Backend serialisiert alle Befehle,
    die die Konfiguration, eine `serie.json` oder den Eingang ändern: **eine Sperre
    für die Konfiguration, eine Sperre je Serie, eine Sperre für den Eingang** (W-21).
    Damit Revision und Dateien nie halb geschrieben werden und keine Verklemmung
    entsteht, gilt eine feste Reihenfolge beim Nehmen mehrerer Sperren: **Eingang,
    dann Serien (nach Serien-ID aufsteigend), dann Warteschlange (seit 13.11., 3.13), dann Konfiguration**; nie umgekehrt.
    Die Seite braucht dafür keine eigene Revision zu schicken.
*   **Aktionen und `ui/*` sind keine eigene Logik** (W-10). Die HA-Aktionen der
    Integration (`services.yaml`, auch für Automationen) und die Eingaben auf
    `tobibox/<box>/ui/…` (`mqtt-v1.md`, 3.8) rufen **dieselben Backend-Funktionen**
    wie die Befehle dieses Vertrags (Sperren, Revision, Reihenfolge H, Vorgang).
    Eine Aktion hat keine Seite und damit keinen Antwortweg: Bei einer Rückfrage
    (Lernmodus, Löschen mit Tobies) gilt `ueberschreiben=false` bzw.
    `tobies_bestaetigt=false`, also Ablehnung, es sei denn, das Aktionsfeld
    (`ueberschreiben`, `tobies_bestaetigt`) ist ausdrücklich `true`.
    `ui/lernen_abbrechen` beendet den Vorgang wie `lernmodus/abbrechen`.
*   **Pfade kommen aus der Serien-Tabelle, nie aus der Eingabe** (Sicherheit). Eine
    Serien-ID, ein Folgenname oder ein Dateiname aus einer Eingabe wird nur als
    Schlüssel nachgeschlagen bzw. nach Abschnitt 12 bereinigt und nie ungeprüft in
    einen Pfad gesetzt.
*   **Namen sind Text.** Namen von Serien, Folgen, Tobies und Dateien stammen aus
    dem Dateisystem oder von Tobias. Die Seite stellt sie **nur als Text** dar,
    nie als HTML (Lit tut das von selbst). Die statischen Dateien der Seite
    (`async_register_static_paths`) verlangen in HA keine Anmeldung: Sie enthalten
    **keine Geheimnisse** (keine Passwörter, keine Adressen); alle Daten kommen über
    die angemeldeten Befehle (W-26).
*   **Sprache.** Namen von Befehlen, Feldern und Codes: ASCII, deutsch, Kleinbuchstaben
    mit `_` (wie in den anderen Verträgen). Texte in `message` und in
    `text`-Feldern: Deutsch, Klartext, für Eltern lesbar. Die Seite darf `message`
    anzeigen, **wertet aber nur `code` aus**.
*   **Format.** JSON, UTF-8. Zeitstempel wie in `data-model.md`
    (`2026-11-05T09:30:00Z`, Millisekunden nur wo angegeben). Kennungen (`uid`)
    kanonisch (`reader-v1.md`, Abschnitt 4). Unbekannte Felder in **Antworten und
    Ereignissen** ignoriert die Seite. Unbekannte Felder in **Eingaben** lehnt HA
    ab (`invalid_format`, siehe 9).
*   **Zeitbudget.** Jeder Befehl antwortet innerhalb von **10 s** (Messung am
    Backend, nicht am Netz). Was länger dauert (Prüfung der Freigabe, `ffprobe`,
    Einsortieren, Prüfsummen), läuft im Hintergrund und meldet sich als Ereignis
    (Abschnitt 4). Dateizugriffe laufen über `hass.async_add_executor_job` (Design,
    Baustein 4). Befehle, die Listen liefern (`serien/list`, `eingang/list`), lesen
    aus dem **Zwischenspeicher** der letzten Prüfung und nie frisch von der Freigabe
    (W-28); nur `serie/get` liest `serie.json` frisch.

## 2. Rechte, Idempotenz, MQTT: die Regeln

### 2.1 Wer darf was (ersetzt am 12.11.)

*Bis 11.11. galt: Lesen für jeden angemeldeten Nutzer, alles andere nur für Administratoren, auch der Upload (W-19). Das ist ersetzt (Entscheidung Tobias, Runde 6: „alle HA-Benutzer“; Wandtablets und Gäste mit Konto sind bewusst eingeschlossen).*

HA prüft bei einem WebSocket-Befehl nur, dass der Nutzer **angemeldet** ist. Wer Administrator sein muss, bestimmt allein der Dekorator `require_admin` am Befehl. Dieser Vertrag kennt drei Stufen:

| Stufe | Wer | Umsetzung |
|---|---|---|
| **lesen** | jeder angemeldete HA-Nutzer | kein Dekorator |
| **alltag** | jeder angemeldete HA-Nutzer | kein Dekorator; für Nicht-Administratoren gelten zusätzlich die Schutzregeln in 2.4 (Zusatzprüfungen im Befehl, Fehler `unauthorized` oder der Code der Prüfung) |
| **admin** | nur Administratoren | `@websocket_api.require_admin`; Fehler `unauthorized` |

**Befehle nach Stufe** (Nr. wie in der Übersicht in Abschnitt 3; Nr. 37 bis 46 sind seit dem 12.11., Nr. 47 bis 49 seit dem 13.11. neu; Nr. 18 bis 20 stehen seit dem 13.11. wieder bei `admin`):

| Stufe | Befehle |
|---|---|
| **lesen** | 1 `hello`, 2 `subscribe`, 3 `serien/list`, 4 `serie/get`, 10 `papierkorb/list`, 13 `neue_tobies/list`, 15 `zuordnung/list`, 21 `boxen/list` (ohne das Feld `ereignisse`), 29 `eingang/list`, 34 `konfig/get`, 35 `einstellungen/get`, 37 `folgen/list`, 40 `hoerstelle/get`, 42 `hoerstelle/liste`; HTTP: Cover (GET), Audio (GET, Anmeldung oder gültige Signatur) |
| **alltag** | 6 `serie/rename`, 8 `folge/delete`, 9 `medien/pruefen`, 14 `neue_tobies/verwerfen`, 16 `zuordnung/set` (mit Name), 17 `zuordnung/remove`, 24 `serie/delete`, 25 `folge/rename`, 26 `folge/verschieben` (Ziel „Überraschungs-Serie“ nur Administratoren), 28 `einsortierung/bestaetigen`, 30 `eingang/sortieren` (ohne `sofort`), 36 `einstellungen/set` (ohne `lesezeichen_tage`; `leise_zeiten.zeitzone` wird ignoriert), 38 `serie/art_setzen`, 39 `audio/bereit`, 41 `hoerstelle/set` (nur die eigene Hörstelle), 43 `einsortierung/neu`, 47 `warteschlange/set`, 48 `warteschlange/list`, 49 `warteschlange/abbrechen`; HTTP: Upload, Cover (POST, DELETE `quelle=eigen`) |
| **admin** | 5 `serie/create`, 7 `folgen/order`, 18 `lernmodus/start`, 19 `lernmodus/antwort`, 20 `lernmodus/abbrechen` (seit 13.11. wieder admin, X13a), 11 `papierkorb/restore`, 12 `papierkorb/empty`, 22 `box/sync`, 23 `liste/neu_ausrollen`, 27 `serien/zusammenfuehren`, 31 `konfig/export_lesen`, 32 `konfig/aus_export`, 33 `eingang/entfernen`, 44 `cover/neu_suchen`, 45 `hoerkopie/neu_erzeugen`, 46 `papierkorb/restore_letzte_stunde`; das Feld `ereignisse` von `boxen/list`; `eingang/sortieren` mit `sofort`; `einstellungen/set` mit `lesezeichen_tage` |

**Lernmodus (seit 13.11.):** `lernmodus/start`, `lernmodus/antwort` und `lernmodus/abbrechen` sind ein Vorgang und wieder nur für Administratoren (X13a). Der Alltag legt neue Tobies über die Warteschlange an (3.13, Recht alltag). Das Ereignisthema `lernmodus` und das Feld `lernmodus` von `boxen/list` bleiben für jeden lesbar (nur Anzeige). *(Lücke im Design: Es sagt nichts zum Lesen des Zustands; unverändert gelassen, weil es nichts auslöst.)*

**Upload (HTTP):** Recht alltag. Der Upload benutzt **keinen** Administrator-Dekorator mehr (**W-19 entfällt**); die Anmeldung prüft HA (`requires_auth`), der Nutzer steht in `request["hass_user"]`. Ohne Anmeldung 401.

**HA-Aktionen** (`services.py`, kein WebSocket-Befehl) ändern etwas und bleiben **nur für Administratoren** (`async_register_admin_service`; Sicherheitsbefund U1, 12.11.). Eine Aktion läuft also nie mit den Schutzregeln aus 2.4 für Nicht-Administratoren.

**Hörstelle:** `hoerstelle/*` arbeitet nur mit der **eigenen** Hörstelle; die Benutzerkennung kommt aus der Verbindung (`connection.user.id`), nie aus der Eingabe. Auch Administratoren sehen keine fremden (Ausnahme: das Backend liest sie intern für die Prüfung in 2.4, zeigt sie aber nirgends). Reinhör-Daten und ihre Rechte (Stufe B): geplant, siehe Design `docs/designs/ha-oberflaeche.md`, Abschnitt 12.

**Die Seite in der Seitenleiste** (`panel_custom`): bleibt `require_admin=True`, **bis Tobias die Abnahme von Teil A-1 gemacht hat**; erst dann öffnet der eigene kleine Schritt „Seite für alle öffnen“ sie (`require_admin=False`). Das blendet die Seite nur aus oder ein und **ersetzt keine Prüfung**: Das Backend prüft bei jedem Aufruf selbst. `hello.darf_schreiben` bleibt „Nutzer ist Administrator“ (der Name bleibt aus Gründen der Verträglichkeit); die Seite blendet „Technik“ danach aus. Das ist Komfort, keine Sicherheit. Die Rechte der Befehle gelten **ab Einführung im Backend**, auch ohne die Seite: Wer per WebSocket aufruft, darf die Alltagsbefehle als Nicht-Administrator benutzen.

**Zu `hello`:** Auch `hello` verrät Version und Box-Namen jedem angemeldeten Nutzer (W-27); in diesem Haushalt harmlos.

### 2.2 Idempotenz

„Idempotent“ heißt hier: **Doppeltes Senden ändert den Endzustand nicht** und
löst keine zweite Wirkung aus (keine zweite MQTT-Nachricht, keine zweite Revision).
Die **Antwort** der zweiten Ausführung kann ein Fehlercode sein; er steht dann in
der Spalte „Doppelt gesendet“.

Befehle, die von Natur aus **nicht** idempotent sind (etwas Neues anlegen oder ein
Ereignis auslösen), nehmen ein optionales Feld **`anfrage_id`** (string, 8–64
Zeichen `[0-9A-Za-z-]`, die Seite erzeugt eine UUID je Knopfdruck). Das Backend
merkt sich die letzten **100** `anfrage_id` mit ihrer Antwort für **10 min** (nur im
Arbeitsspeicher, ein HA-Neustart vergisst sie) und liefert bei gleicher
`anfrage_id` und gleichem Befehl dieselbe Antwort erneut, **ohne** die Wirkung zu
wiederholen. Gleiche `anfrage_id` mit anderem Befehl oder anderen Feldern:
`anfrage_id_konflikt`. **Nur Erfolge werden gemerkt** (W-22): Wiederholt die Seite
nach einem Fehler (z. B. `mqtt_nicht_verbunden`) mit derselben `anfrage_id`, führt das
Backend den Befehl neu aus und liefert nicht den gemerkten Fehler.

### 2.3 Zusammenhang mit MQTT

Jeder Befehl nennt in „MQTT“, was er auslöst. Zusammengefasst:

| Wirkung auf MQTT | Befehle |
|---|---|
| veröffentlicht `tobibox/config` (retained, Revision + 1) | `zuordnung/set`, `zuordnung/remove`, `lernmodus/antwort`, Lernmodus-Zuordnung (6.2), Zuordnung durch die Warteschlange beim Auflegen (3.13), `folge/verschieben` und `serien/zusammenfuehren` (nur wenn Tobies auf die verschobenen Folgen zeigen), `einstellungen/set` (nur bei einer Änderung) |
| veröffentlicht `tobibox/config` mit **neuer Listen-ID** | `liste/neu_ausrollen`, `konfig/aus_export` |
| sendet `tobibox/<box>/cmd` (mit `id`, `erzeugt`, `ttl_s`) | `lernmodus/start` (`lernen`, 60 s), `lernmodus/abbrechen` (`lernen_abbrechen`, 30 s), `box/sync` (`sync`, 300 s), später `box/update` (`update`, 300 s) |
| sendet `tobibox/<box>/unknown/<uid>/ack` | der Lernmodus (6.2: `zugeordnet`, `abgelehnt`). Die Bestätigung beim ersten Eintreffen einer Kennung (`neu`, `bekannt`) ist **Sache des Backends allein**, kein Befehl der Seite (`mqtt-v1.md`, 3.6). |
| nichts | alle übrigen (Medien, Eingang, Papierkorb, Lesen, Verwerfen, `warteschlange/set`, `warteschlange/list`, `warteschlange/abbrechen`) |

Die **Reihenfolge** „erst Konfiguration, dann `ack`“ (Entscheidung H, 07.11.;
`mqtt-v1.md`, 4.2) gilt für jeden Weg, der eine Zuordnung schreibt und danach
bestätigt, und zwar **erst nach dem PUBACK** der Konfiguration (6.2, Schritt 4).

### 2.4 Schutz gegen Fehlbedienung und Mengen (neu 12.11.)

Weil „alltag“ alle HA-Benutzer meint, gilt für **Nicht-Administratoren** zusätzlich das Folgende. Administratoren sind davon ausgenommen, soweit nicht anders gesagt. Konstanten stehen in Abschnitt 14.10.

*   **`zuordnung/remove` nur mit `erwartet_ziel`;** `zuordnung/set` mit `ueberschreiben=true` ebenso nur mit `erwartet_ziel`. Fehlt es: `unauthorized`. Stimmt es nicht: `zuordnung_geaendert`. (Die Seite sendet es immer, 3.5.)
*   **`zuordnung/set` nur für bekannte Kennungen:** Die Kennung steht in `neue_tobies`, ist Ergebnis eines Lernmodus oder ist schon zugeordnet; sonst `kennung_ungueltig`.
*   **`eingang/sortieren` ohne `sofort`:** `sofort=true` von einem Nicht-Administrator: `unauthorized`. Die Ruhezeit schützt halb kopierte Dateien.
*   **`einstellungen/set`:** Das Backend **ignoriert** `leise_zeiten.zeitzone` im Objekt und behält den gespeicherten Wert (kein `unauthorized`); `lesezeichen_tage` von einem Nicht-Administrator: `unauthorized`. Neue optionale Eingabe `erwartet_revision` (3.11): stimmt sie nicht mit `konfig.revision` überein, Fehler `stand_veraltet`.
*   **`folge/verschieben` mit der Überraschungs-Serie als Ziel:** Nicht-Administratoren bekommen `ziel_ungueltig` (die Serie bestimmt, was die Box beim unbekannten Tobie spielt).
*   **Mengen** (je Benutzer, darüber `zu_viele_aenderungen`, HTTP 429; Zähler getrennt je Art): höchstens `AENDERUNGEN_JE_MINUTE` Änderungen der Liste (`zuordnung/set`, `zuordnung/remove`, `einstellungen/set`), höchstens `PAPIERKORB_AKTIONEN_JE_10_MIN` Papierkorb-Aktionen (`folge/delete`, `serie/delete`, `einsortierung/neu`), höchstens `UPLOAD_BYTES_JE_STUNDE` Upload, höchstens `COVER_JE_STUNDE` Cover-Uploads, höchstens `HOERSTELLE_SCHREIBEN_JE_MINUTE` Aufrufe von `hoerstelle/set`, höchstens `AUDIO_BEREIT_JE_MINUTE` Aufrufe von `audio/bereit`, höchstens `WARTESCHLANGE_AENDERUNGEN_JE_MINUTE` Aufrufe von `warteschlange/set` und `warteschlange/abbrechen` zusammen (seit 13.11.; ein Treffer beim Auflegen zählt nicht, er ist keine Handlung eines Benutzers). Die Liste bleibt unter `KONFIG_MAX_BYTES`, weil Kennungen nur bekannt oder gemeldet sein dürfen.
*   **Frühere Stände der Liste:** Die Integration behält die letzten `KONFIG_STAENDE_ANZAHL` Stände als `export/config.<n>.json` (`<n>` = 1 der jüngste frühere Stand) zusätzlich zu `export/config.json`. Lesen und Zurückspielen (beides admin): `konfig/export_lesen` und `konfig/aus_export` bekommen die optionale Eingabe `stand` (ganze Zahl 1 bis `KONFIG_STAENDE_ANZAHL`; fehlt sie, gilt der aktuelle Export wie bisher); `konfig/export_lesen` gibt zusätzlich `staende` aus (Liste aus `stand`, `exportiert_am`, `anzahl_zuordnungen`). Fähigkeit `konfig_staende`. Fehler wie bisher, dazu `export_nicht_gefunden` für einen Stand, den es nicht gibt. *(Ergänzung zum Design: Das Design nennt „Frühere Stände ansehen“ und „Aus Stand wiederherstellen“, legt die Schnittstelle aber nicht fest.)*
*   **Papierkorb für Alltag:** Löschen mit Tobies verlangt wie bisher `tobies_bestaetigt`. (a) **Keine HA-Mitteilung** (Änderung 14.11., AC3, Tobias: HA-Mitteilungen sehen alle Benutzer): Die Seite zeigt Administratoren einen Punkt am Technik-Symbol, wenn andere Benutzer seit dem letzten Besuch etwas in den Papierkorb gelegt haben (aus `papierkorb/list`, `geloescht_von`, `geloescht_am`). (b) Jede Papierkorb-Aktion schreibt eine Protokollzeile (Benutzer, Zeit, Eintrag) und merkt `geloescht_von` im Papierkorb-Eintrag (3.3). (c) `papierkorb/restore_letzte_stunde` (Nr. 46) holt zurück, was in der letzten Stunde hineinkam. Es gibt **kein Tageslimit**.
*   **`einsortierung/neu` (Nr. 43):** nimmt nur Einträge aus `eingang/list`, die `pruefen=true` sind **oder** höchstens `EINSORTIERUNG_NEU_ALTER_MAX_S` alt (seit `fertig_am`); sonst `neu_einsortieren_nicht_moeglich`. Es zählt als Papierkorb-Aktion, die Ruhezeit gilt wie beim Einsortieren. **Liste der „etwas geändert“-Prüfungen** (jede einzelne genügt für `neu_einsortieren_nicht_moeglich`): (1) eine der betroffenen Serien oder Folgen wurde umbenannt; (2) eine Folge wurde in eine andere Serie verschoben oder die Reihenfolge der Folgen wurde geändert (der `stand` der Serie weicht von dem ab, den das Protokoll nach dem Einsortieren gemerkt hat); (3) ein Tobie zeigt auf eine betroffene Serie oder Folge; (4) `art_quelle` einer betroffenen Serie ist `manuell`; (5) eine betroffene Serie hat ein eigenes Cover (`cover-eigen.jpg`); (6) irgendein Benutzer hat eine betroffene Folge angehört (das Backend liest dafür **intern** auch fremde Hörstellen und zeigt sie nirgends); (7) in einer Serie, die der Eintrag neu angelegt hatte, liegen Folgen, die nicht von diesem Eintrag stammen.
*   **Warteschlange (seit 13.11., 3.13):** Anlegen und Abbrechen für alle Benutzer (Recht alltag) unter der Menge oben und der Höchstzahl `WARTESCHLANGE_MAX`. Die Zuordnung beim Auflegen läuft als System (kein Benutzer, keine Mengen) und **hängt nie einen bekannten Tobie um**; sie nimmt nur Kennungen, die eine Box gerade gemeldet hat und die noch kein Ziel haben. Jede Anlage, jedes Abbrechen und jeder Treffer schreibt eine Protokollzeile; eine Mitteilung an Administratoren gibt es nicht (3.13, Regel 13).
*   **Vorziehen von Hörkopien:** je Benutzer höchstens `HOERKOPIE_VORZIEHEN_JE_BENUTZER` Datei zugleich (14.8).
*   **Audio:** höchstens `AUDIO_VERBINDUNGEN_JE_BENUTZER` offene Audio-Verbindungen je Benutzer (14.5). Der HA-eigene Befehl `auth/sign_path` darf jeder angemeldete Benutzer aufrufen; die Signatur trägt seine Identität und gibt ihm keine Rechte, die er nicht ohnehin hat.

## 3. Befehle

Alle Befehle heißen `tobibox/…`. Die HA-Nachricht ist `{"id": <int>, "type":
"tobibox/…", …Felder}`; die Antwort `{"id", "type": "result", "success": true,
"result": …}` oder `{"id", "type": "result", "success": false, "error": {"code",
"message"}}` (Format von HA). **„Ausgabe“ unten ist der Inhalt von `result`.**
Pflichtfelder sind fett. Fehlercodes: Tabelle in Abschnitt 7.

### Übersicht

| Nr. | Befehl | Recht (2.1) | Idempotent | MQTT |
|---|---|---|---|---|
| 1 | `tobibox/hello` | lesen | ja | – |
| 2 | `tobibox/subscribe` | lesen | ja (je Abo neu) | – |
| 3 | `tobibox/serien/list` | lesen | ja | – |
| 4 | `tobibox/serie/get` | lesen | ja | – |
| 5 | `tobibox/serie/create` | admin | mit `anfrage_id` | – |
| 6 | `tobibox/serie/rename` | alltag | ja | – |
| 7 | `tobibox/folgen/order` | admin | ja | – |
| 8 | `tobibox/folge/delete` | alltag | ja (Endzustand) | – |
| 9 | `tobibox/medien/pruefen` | alltag | ja | – |
| 10 | `tobibox/papierkorb/list` | lesen | ja | – |
| 11 | `tobibox/papierkorb/restore` | admin | ja (Endzustand) | – |
| 12 | `tobibox/papierkorb/empty` | admin | ja | – |
| 13 | `tobibox/neue_tobies/list` | lesen | ja | – |
| 14 | `tobibox/neue_tobies/verwerfen` | alltag | ja | – |
| 15 | `tobibox/zuordnung/list` | lesen | ja | – |
| 16 | `tobibox/zuordnung/set` | alltag | ja | `tobibox/config` |
| 17 | `tobibox/zuordnung/remove` | alltag | ja | `tobibox/config` |
| 18 | `tobibox/lernmodus/start` | admin | mit `anfrage_id` | `…/cmd` `lernen` |
| 19 | `tobibox/lernmodus/antwort` | admin | ja (Endzustand) | `tobibox/config`, dann `…/ack` |
| 20 | `tobibox/lernmodus/abbrechen` | admin | ja | `…/cmd` `lernen_abbrechen` |
| 21 | `tobibox/boxen/list` | lesen | ja | – |
| 22 | `tobibox/box/sync` | admin | mit `anfrage_id` | `…/cmd` `sync` |
| 23 | `tobibox/liste/neu_ausrollen` | admin | mit `anfrage_id` | `tobibox/config` (neue Listen-ID) |
| 24 | `tobibox/serie/delete` | alltag | ja (Endzustand) | – |
| 25 | `tobibox/folge/rename` | alltag | ja | – |
| 26 | `tobibox/folge/verschieben` | alltag | ja (Endzustand) | `tobibox/config` (nur bei betroffenen Tobies) |
| 27 | `tobibox/serien/zusammenfuehren` | admin | ja (Endzustand) | `tobibox/config` (nur bei betroffenen Tobies) |
| 28 | `tobibox/einsortierung/bestaetigen` | alltag | ja | – |
| 29 | `tobibox/eingang/list` | lesen | ja | – |
| 30 | `tobibox/eingang/sortieren` | alltag | ja | – |
| 31 | `tobibox/konfig/export_lesen` | admin | ja | – |
| 32 | `tobibox/konfig/aus_export` | admin | mit `anfrage_id` | `tobibox/config` (neue Listen-ID) |
| 33 | `tobibox/eingang/entfernen` | admin | ja (Endzustand) | – |
| 34 | `tobibox/konfig/get` | lesen | ja | – |
| 35 | `tobibox/einstellungen/get` | lesen | ja | – |
| 36 | `tobibox/einstellungen/set` | alltag | ja | `tobibox/config` (nur bei einer Änderung) |
| 37 | `tobibox/folgen/list` | lesen | ja | – |
| 38 | `tobibox/serie/art_setzen` | alltag | ja | – |
| 39 | `tobibox/audio/bereit` | alltag | ja | – |
| 40 | `tobibox/hoerstelle/get` | lesen | ja | – |
| 41 | `tobibox/hoerstelle/set` | alltag | ja | – |
| 42 | `tobibox/hoerstelle/liste` | lesen | ja | – |
| 43 | `tobibox/einsortierung/neu` | alltag | nein | – |
| 44 | `tobibox/cover/neu_suchen` | admin | ja | – |
| 45 | `tobibox/hoerkopie/neu_erzeugen` | admin | ja | – |
| 46 | `tobibox/papierkorb/restore_letzte_stunde` | admin | ja (Endzustand) | – |
| 47 | `tobibox/warteschlange/set` | alltag | mit `anfrage_id` | – |
| 48 | `tobibox/warteschlange/list` | alltag | ja | – |
| 49 | `tobibox/warteschlange/abbrechen` | alltag | ja | – |

Dazu der HA-eigene Befehl `unsubscribe_events` zum Beenden eines Abos (Abschnitt 4).
Die Befehle 33 bis 36 sind seit dem 09.11. (AP 4.7) gültig; ihre Fähigkeiten stehen in `hello`.
Die Befehle 37 bis 46 und die Stufen `lesen`, `alltag`, `admin` sind seit dem 12.11. festgelegt (Abschnitt 2.1, 3.12, 14); an den Befehlen 1 bis 36 steht „Recht“ statt „Rechte“. Die Befehle 47 bis 49 (Abschnitt 3.13) sind seit dem 13.11. festgelegt; seit dem 13.11. sind 18 bis 20 wieder `admin`.
**Reserviert** für später (Namen sind vergeben, der Inhalt kommt in der jeweiligen
Stufe): Abschnitt 10.

### Gemeinsame Objekte

**Ziel** (wie `ziel` in `config.json`, `data-model.md`, Abschnitt 2):

```json
{ "typ": "serie", "serie": "3f9a1c07b2d4" }
{ "typ": "folge", "serie": "8c21d5e9a0b7", "folge": "folge-03.mp3" }
{ "typ": "aktion", "aktion": "status" }
```

**Konfig-Stand** (`konfig`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `revision` | int | wie in `tobibox/config` |
| `liste_id` | string | wie in `tobibox/config` |
| `zustand` | `ok`, `leer_neu`, `export_neuer` | Zustand der Konfiguration (Abschnitt 13). Nur bei `ok` verteilt die Integration etwas. |
| `export_ok` | bool | der Export auf das NAS entspricht dem Stand im HA-Speicher (W-06) |
| `export_geschrieben_am` | string oder `null` | wann der Export zuletzt geschrieben wurde |

Nur `revision` und `liste_id` stehen auch in der MQTT-Nachricht; die anderen Felder
sind Zustand in HA. Im Zustand `leer_neu` sind `revision` und `liste_id` `null`.

**Tobie-Kurzform** (`betroffene_tobies`, `tobies`, `zuordnungen`):
`{"uid": <string>, "name": <string oder null>}` (`name`: Tobie-Name aus der
Zuordnung, `data-model.md`, Abschnitt 2).

**Serie-Kurzform** (`serien/list`, `serie/create`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | Serien-ID (`serie.json`) |
| `name` | string | Anzeigename |
| `typ` | `normal` oder `ueberraschung` | wie in `serie.json` |
| `ordner` | string | Ordnername auf der Freigabe (nur zur Anzeige) |
| `anzahl_folgen` | int | Länge von `folgen` |
| `anzahl_tobies` | int | Tobies, deren `ziel` auf diese Serie zeigt (`serie` und `folge`) |
| `angelegt_am` | string | Zeitstempel |
| `stand` | string | Fingerabdruck (16 Zeichen `[0-9a-f]`) von `name`, `folgen` und den **von Menschen gesetzten** Feldern von `folgen_info` (`anzeige`, `nummer`, `datum`, `pruefen`); ändert sich auch, wenn jemand `serie.json` von außen ändert, **nie** durch Hintergrundläufe oder Werte aus dem Store `tobibox.medieninfo` (seit 12.11.; vorher rechnete er über das ganze `folgen_info`) |
| `pruefen` | bool | die Serie selbst ist „bitte prüfen“ (Abschnitt 11.9) |
| `anzahl_pruefen` | int | Folgen dieser Serie mit „bitte prüfen“ |
| `hinweise` | array | Hinweise zu dieser Serie, siehe unten |
| *(seit 12.11.)* | | weitere Ausgabefelder `art`, `art_quelle`, `einzeln`, `kapitel_anzahl`, `dauer_s`, `cover_stand`, `cover_quelle`, `hoerstelle`: 14.2 |

**Hinweis** (`hinweise[]`): `{"code": <string>, "folge": <string oder null>, "text": <string>}`.
Codes in Version 1: `datei_fehlt` (Name steht in `folgen`, Datei fehlt; die Integration
nimmt ihn beim nächsten Prüfen heraus), `kopierschutz` (D5, Codec `drms`),
`nicht_lesbar` (`ffprobe` öffnet die Datei nicht), `probedekodierung_fehlgeschlagen`,
`pruefung_nicht_moeglich` (`ffprobe` fehlt), `serie_name_doppelt` (12.11., 14.4), `doppelte_id_korrigiert` (die
Integration hat dieser jüngeren Kopie eine neue ID gegeben, `data-model.md`,
Abschnitt 5), `serie_json_ungueltig_repariert`, `reservierter_ordner` (ein Ordner mit
reserviertem Namen liegt in `medien/`, Abschnitt 12). Unbekannte Codes zeigt die Seite
mit `text`. Die Hinweise zu Dateien, die **von außen** in einen Serien-Ordner kamen,
bleiben wie in Version 1 von der Prüfung (`medien/pruefen`) bestimmt; für Dateien
im Eingang gilt Abschnitt 11.10.

### 3.1 Allgemein

#### 1. `tobibox/hello`

Erster Aufruf der Seite nach dem Laden. Prüft die Vertragsversion und liefert, was
die Seite zum Start braucht.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `v` | int | ja | Vertragsversion, die die Seite kennt (hier `1`) |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `v` | int | Vertragsversion des Backends |
| `version` | string | Version der Integration (`manifest.json`) |
| `darf_schreiben` | bool | der angemeldete Nutzer ist Administrator |
| `faehigkeiten` | array von string | was das Backend kann; Version 1 (Stufe 3a): `medien`, `upload`, `zuordnung`, `tobie_namen`, `neue_tobies`, `lernmodus`, `boxen`, `papierkorb`, `liste_ausrollen`, `konfig_export`, `sync`, `eingang`, `korrektur`, `serie_loeschen`. **(09.11., AP 4.7)** Dazu `einstellungen` (Befehle 35 und 36), `eingang_entfernen` (Nr. 33), `zuordnung_uid` (Eingabe `uid` bei Nr. 15), `konfig_lesen` (Nr. 34) und `upload_fertig_details` (`datei` und `pruefung` im Ereignis „Upload fertig“, 4.7). **(12.11., Stufe A der HA-Oberfläche)** Dazu, nach Teil gebaut: `cover`, `bibliothek`, `einsortier_wunsch`, `konfig_staende`, `reinhoeren`, `hoerkopie` (Regel und Bedeutung: 14.1). **(13.11., A0-Q)** Dazu `warteschlange` und `zuordnung_rueckgaengig` (14.1). Spätere Stufen ergänzen `update` (3b). Die Reihenfolge der Liste hat keine Bedeutung (K4, 12.11.). Die Seite zeigt und sendet nur, was hier steht. |
| `boxen` | array von string | die eingerichteten Box-Namen (aus der Einrichtung der Integration) |
| `konfig` | object | Konfig-Stand mit `zustand`. Ist `zustand` nicht `ok`, zeigt die Seite zuerst die Warnung aus Abschnitt 13 und sperrt Änderungen der Konfiguration. |
| `grenzen` | object | `upload_max_bytes` (Vorgabe seit 12.11. 2147483648 = 2 GiB, einstellbar; vorher 500 MiB), `upload_block_bytes`, `upload_parallel` (2), `endungen` (array), `serie_name_max` (100), `folge_anzeige_max` (200), `tobie_name_max` (60), `name_max_bytes` (255), `limit_max` (100 bzw. 200, je Befehl); **(12.11.)** bei zugesagter Fähigkeit dazu `audio_verbindungen_je_benutzer` (6), `hoerkopie_kbit` (96), `hoerkopie_dauer_max_s` (14.10); **(13.11.)** bei Fähigkeit `warteschlange` dazu `warteschlange_max` (5). Außerdem `box_anzeigen` (object: Box-Name → Anzeigename, 14.9) im Ergebnis von `hello` |

Fehler: keine außer den allgemeinen. Ist `v` der Seite **größer** als das Backend
kennt, antwortet das Backend trotzdem mit seinem `v`; die Seite entscheidet
(Abschnitt 9). Recht: lesen. Idempotent: ja. MQTT: –.

#### 2. `tobibox/subscribe`

Abonniert Ereignisse (Abschnitt 4). Ein Abo je Seite genügt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `themen` | array von string | nein | Teilmenge von `boxen`, `neue_tobies`, `lernmodus`, `medien`, `eingang`, `konfig`, `upload`; **(13.11.)** dazu `warteschlange` (nur senden, wenn `hello.faehigkeiten` `warteschlange` zusagt); Vorgabe: alle |

Ausgabe: `null` (HA-Muster). Danach kommen die Ereignisse als `{"id": <id des Abos>,
"type": "event", "event": {…}}`. Direkt nach der Antwort sendet das Backend je
Thema ein Ereignis mit `art="snapshot"` (Abschnitt 4). Beenden: HA-Befehl
`unsubscribe_events` mit `subscription` = `id` des Abos. Recht: lesen.
Idempotent: jedes Abo ist unabhängig; zweimal abonnieren heißt doppelte
Ereignisse. MQTT: –.

### 3.2 Serien und Folgen

#### 3. `tobibox/serien/list`

Keine Eingabe. Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `serien` | array von Serie-Kurzform | sortiert nach Name (natürliche Sortierung, `data-model.md`, Abschnitt 5) |
| `ueberraschung` | `"ok"`, `"fehlt"`, `"mehrere"` oder `"leer"` | Zustand der Überraschungs-Serie (Box spielt sonst Fehlerton, `data-model.md`, Abschnitt 5). Bei `fehlt` bietet die Seite „Überraschungs-Serie anlegen“ (`serie/create` mit `typ="ueberraschung"`). |
| `geprueft_am` | string oder `null` | wann die Integration die Freigabe zuletzt geprüft hat |
| `pruefung_laeuft` | bool | eine Prüfung läuft gerade |
| `hinweise` | array | **(09.11., Befund AP 3.1, additiv)** Hinweise, die zu keiner Serie gehören: je reserviertem Ordner in `medien/` (Abschnitt 12) ein Objekt `{"code": "reservierter_ordner", "folge": <Ordnername>, "text": <Text>}` (`folge` trägt hier den Ordnernamen). Leer, wenn es keinen gibt. Die Systemordner `_upload` und `_papierkorb` stehen nicht darin. |

Die Antwort kommt aus dem **Zwischenspeicher** der letzten Prüfung (W-28); `geprueft_am`
zeigt sein Alter. Das Backend liest für diesen Befehl keine `serie.json` frisch von
der Freigabe. Fehler: `medien_nicht_erreichbar` (nur, wenn noch nie geprüft wurde).
Recht: lesen. Idempotent: ja. MQTT: –.

#### 4. `tobibox/serie/get`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | Serien-ID |

Liest `serie.json` frisch. Ausgabe: die Felder der Serie-Kurzform und dazu

| Feld | Typ | Bedeutung |
|---|---|---|
| `folgen` | array | in der maßgeblichen Reihenfolge (`serie.json`), Objekte siehe unten |
| `zuordnungen` | array von Tobie-Kurzform | Tobies, die auf die **ganze Serie** zeigen (Folgen-Tobies stehen bei der Folge) |

Folge-Objekt:

| Feld | Typ | Bedeutung |
|---|---|---|
| `name` | string | Dateiname oder Ordnername (Schlüssel, `data-model.md`, 1.1). Er ändert sich nie durch Umbenennen. |
| `anzeige` | string | Anzeigename: `folgen_info.<name>.anzeige`, sonst der `name` ohne Endung |
| `nummer` | int oder `null` | Folgen-Nummer (aus den Tags oder dem Albumnamen, Abschnitt 11) |
| `datum` | string oder `null` | Erscheinungsdatum `YYYY-MM-DD` |
| `art` | `datei` oder `ordner` | Datei im Serien-Ordner oder Unterordner mit mehreren Tracks (Entscheidung F) |
| `tracks` | int ≥ 1 | Anzahl Tracks (`datei`: 1) |
| `groesse_bytes` | int | Summe der Dateigrößen |
| `pruefung` | `ok`, `warnung`, `nicht_geprueft`, `nicht_moeglich` | Ergebnis der Prüfung nach D5 |
| `hinweis` | string oder `null` | Code aus der Hinweisliste, bei `warnung` |
| `pruefen` | bool | „bitte prüfen“ (Abschnitt 11.9) |
| `pruefen_gruende` | array von string | Codes aus 11.9, leer wenn `pruefen=false` |
| `tobies` | array von Tobie-Kurzform | Tobies, deren `ziel` genau auf diese Folge zeigt |

Fehler: `serie_nicht_gefunden`, `medien_nicht_erreichbar`. Recht: lesen.
Idempotent: ja. MQTT: –.

#### 5. `tobibox/serie/create`

Legt eine neue Serie an (Ordner + `serie.json` mit neuer zufälliger ID, `angelegt_am`
jetzt, `folgen` leer; D2, D4).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `name` | string, 1–100 Zeichen | **ja** | Anzeigename; nach dem Abschneiden von Leerraum nicht leer |
| `typ` | `normal` oder `ueberraschung` | nein | Vorgabe `normal`. `ueberraschung` nur, wenn es noch keine gibt (`ueberraschung_existiert`). Die Seite bietet es an, wenn `serien/list` `ueberraschung="fehlt"` meldet. |
| `anfrage_id` | string | nein | siehe 2.2 |

Der **Ordnername** entsteht aus dem Namen nach den Namensregeln (Abschnitt 12); gibt
es den Ordner schon (ohne Rücksicht auf Groß-/Kleinschreibung), hängt das Backend
` (2)`, ` (3)` … an. Der Ordnername ist **nicht** die ID (die ID ist zufällig); er
ändert sich später nie, auch nicht beim Umbenennen.

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `name_ungueltig`,
`ueberraschung_existiert`, `medien_nicht_erreichbar`, `medien_schreibfehler`,
`anfrage_id_konflikt`. Recht: admin. Idempotent: **nicht** ohne `anfrage_id` (zweimal
gesendet gibt zwei Serien); mit gleicher `anfrage_id` nur einmal. MQTT: –. Die Boxen
sehen die Serie nach dem nächsten Sync.

#### 6. `tobibox/serie/rename`

Ändert den **Anzeigenamen** `name` in `serie.json` (Vorgabe der Projektleitung 09.11.).
Die ID und der Ordnername bleiben; Zuordnungen und Zeiger bleiben deshalb gültig,
es geht nie ein Zeiger verloren. Löscht das Kennzeichen `pruefen` der Serie.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `name` | string, 1–100 Zeichen | **ja** | neuer Anzeigename |

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `serie_nicht_gefunden`,
`name_ungueltig`, `medien_schreibfehler`. Recht: alltag. Idempotent: ja (gleicher
Name: nichts geschrieben). MQTT: –. Nebenwirkung: Die Box zeigt den neuen Namen im
Status (`serie.name`) und in der Auswahl `lern_serie` erst nach dem Sync
(`mqtt-v1.md`, 6.2).

#### 7. `tobibox/folgen/order`

Setzt die Reihenfolge der Folgen (die Seite sortiert per Ziehen und schickt die
**ganze Liste**).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folgen` | array von string | **ja** | alle Namen der Folgen (`name`, nicht `anzeige`) in der neuen Reihenfolge |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** (W-12) | `stand` aus `serie/get`. Stimmt er nicht mehr (jemand hat `serie.json` oder den Ordner von außen geändert), lehnt das Backend ab (`stand_veraltet`) und die Seite lädt neu. Ohne `stand` gilt „letzter Schreiber gewinnt“; das ist nur für Aktionen und Automationen gedacht. |

Die Liste muss eine **Umstellung** der aktuellen Liste sein: dieselben Namen, ohne
Doppelte, nichts fehlt, nichts kommt dazu. Sonst `reihenfolge_ungueltig`.

Ausgabe: `{"serie": <Serie-Kurzform>}` (mit neuem `stand`). Fehler:
`serie_nicht_gefunden`, `reihenfolge_ungueltig`, `stand_veraltet`,
`medien_schreibfehler`. Recht: admin. Idempotent: ja. MQTT: –. Nebenwirkung: Die
Box spielt die neue Reihenfolge nach dem Sync; der Zeiger einer Serie (Folge als
Name) bleibt gültig (`data-model.md`, Abschnitt 3).

#### 8. `tobibox/folge/delete`

Verschiebt eine Folge (Datei oder Folgen-Ordner) in den Papierkorb und nimmt sie
aus `folgen` und `folgen_info`. Nie endgültig (Design: „Löschen verschiebt in `_papierkorb/`“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name der Folge |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Folge, lehnt das Backend ohne `true` ab (`tobies_betroffen`). Die Seite fragt Tobias mit Anzahl und **Namen** der Tobies (aus `serie/get`, Feld `tobies`) und sendet erneut mit `true` (Vorgabe der Projektleitung 09.11.). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `eintrag` | object | Papierkorb-Eintrag (siehe 3.3) |
| `betroffene_tobies` | array von Tobie-Kurzform | Tobies mit `ziel.typ="folge"` auf diese Folge. Ihre Zuordnung **bleibt unverändert** (Revision wird nicht erhöht); die Box spielt für sie die Überraschungs-Serie (`folge_fehlt`), bis die Folge zurück ist (`data-model.md`, Abschnitt 2). Die Seite zeigt den Hinweis. |

Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `tobies_betroffen`,
`stand_veraltet`, `medien_schreibfehler`. Recht: alltag. Idempotent: Endzustand ja;
der zweite Aufruf liefert `folge_nicht_gefunden`. MQTT: –. Nebenwirkung: Die Box
löscht ihre Kopie beim nächsten Sync (`--delete`, mit Schutz).

#### 9. `tobibox/medien/pruefen`

Stößt die Prüfung der Freigabe an (Design: „beim Öffnen der Seite und alle
10 min“): neue Ordner (→ `serie.json` mit neuer ID, Ordnername als Name; für
Ordner ohne Datei die ID = Ordnername, damit Zeiger und Zuordnungen erhalten bleiben
(`data-model.md`, Abschnitt 5; ist der Ordnername als ID ungültig, eine neue zufällige ID)
(09.11., Befund AP 3.1), neue Dateien und
neue Folgen-Ordner (→ hinten an `folgen`), fehlende Dateien (→ heraus, Hinweis),
doppelte Serien-IDs (→ jüngere Kopie bekommt neue ID), Format- und Kopierschutz-
Prüfung neuer Dateien (D5). Das gilt für Dateien, die **von außen direkt in einen
Serien-Ordner** kamen (z. B. vom PC); sie werden wie in Version 1 aufgenommen und bei
Kopierschutz mit `pruefung="warnung"` markiert. Die Prüfung ignoriert die reservierten
Ordner (Abschnitt 12: `_…`, `eingang`). Der Eingang ist **nicht** Teil dieser
Prüfung; ihn bearbeitet `eingang/sortieren` (Nr. 30), und der 10-min-Timer ruft
beide nacheinander auf.

Keine Eingabe. Ausgabe: `{"gestartet": <bool>, "laeuft_bereits": <bool>}`. Die
Prüfung selbst läuft im Hintergrund; ihr Ende kommt als Ereignis `medien` mit
`art="pruefung_fertig"` (4.4). Läuft schon eine Prüfung (Timer oder anderer Nutzer),
meldet der Befehl `laeuft_bereits=true` und startet keine zweite.

Fehler: `medien_nicht_erreichbar`. Recht: alltag. Idempotent: ja. MQTT: –.

#### 24. `tobibox/serie/delete`

Verschiebt eine **ganze Serie** (Ordner mit `serie.json`, Dateien und Folgen-Ordnern)
in den Papierkorb (Vorgabe der Projektleitung 09.11.). Nie endgültig.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Serie oder auf eine ihrer Folgen, lehnt das Backend ohne `true` ab (`tobies_betroffen`). Die Seite fragt mit Anzahl und Namen (`serie/get`: `zuordnungen` und `tobies` der Folgen). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe: `{"eintrag": <Papierkorb-Eintrag, typ "serie">, "betroffene_tobies": [<Tobie-Kurzform>…],
"ueberraschung": <wie bei serien/list, nach dem Löschen>}`. Die Zuordnungen **bleiben**
(keine neue Revision); die Box spielt bis zur Wiederherstellung die Überraschung
(`serie_fehlt`, `folge_fehlt`). Wird die Überraschungs-Serie gelöscht, meldet
`ueberraschung="fehlt"` das.

Fehler: `serie_nicht_gefunden`, `tobies_betroffen`, `stand_veraltet`,
`medien_nicht_erreichbar`, `medien_schreibfehler`. Recht: alltag. Idempotent:
Endzustand ja; der zweite Aufruf liefert `serie_nicht_gefunden`. MQTT: –.
Nebenwirkung: Die Box löscht ihre Kopie beim nächsten Sync (`--delete`, mit Schutz
bei mehr als 20 % Löschungen, AP 3.4).

#### 25. `tobibox/folge/rename`

Ändert nur den **Anzeigenamen** einer Folge (`folgen_info.<name>.anzeige` in
`serie.json`; Vorgabe der Projektleitung 09.11.). Der Dateiname oder Ordnername
(der Schlüssel) bleibt; Zuordnungen (`ziel.folge`) und Zeiger bleiben gültig, es geht
nie ein Zeiger verloren. Löscht das Kennzeichen `pruefen` dieser Folge.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name (Schlüssel) der Folge |
| `name` | string, 1–200 Zeichen | **ja** | neuer Anzeigename |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | wie bei `folgen/order` |

Ausgabe: `{"serie": <Serie-Kurzform>, "folge": <Folge-Objekt>}`. Fehler:
`serie_nicht_gefunden`, `folge_nicht_gefunden`, `name_ungueltig`, `stand_veraltet`,
`medien_schreibfehler`. Recht: alltag. Idempotent: ja (gleicher Name: nichts
geschrieben). MQTT: –.

#### 26. `tobibox/folge/verschieben`

Verschiebt eine Folge in eine **andere Serie** (Korrektur nach dem Einsortieren,
Entscheidung M). Die Dateien wechseln den Serien-Ordner (Umbenennen auf derselben
Freigabe), `folgen` und `folgen_info` beider Serien werden fortgeschrieben, die Folge
wird nach der Regel aus 11.6 in die Zielserie eingefügt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | bisherige Serie |
| `folge` | string | **ja** | Name der Folge |
| `ziel_serie_id` | string | **ja** | neue Serie (darf für Administratoren die Überraschungs-Serie sein, für Nicht-Administratoren seit 12.11. nicht: `ziel_ungueltig`; nicht dieselbe wie `serie_id`: `ziel_ungueltig`; kein Einzeltitel, 14.2) |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf diese Folge (`ziel.typ="folge"`), lehnt das Backend ohne `true` ab (`tobies_betroffen`). |
| `stand` | string | nein im Schema, **die Seite muss ihn senden** | `stand` der bisherigen Serie |

Gibt es im Zielordner schon eine Datei oder einen Ordner gleichen Namens (ohne
Rücksicht auf Groß-/Kleinschreibung), erhält die Folge ein Suffix (Abschnitt 12); der
neue Name steht in der Ausgabe.

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `quelle`, `ziel` | Serie-Kurzform | beide Serien nach dem Verschieben |
| `folge` | string | Name der Folge in der Zielserie (kann vom alten Namen abweichen) |
| `betroffene_tobies` | array von Tobie-Kurzform | Folgen-Tobies, deren `ziel` umgeschrieben wurde (`ziel.serie` und gegebenenfalls `ziel.folge`) |
| `konfig` | object oder `null` | Konfig-Stand, wenn die Konfiguration geändert wurde (Revision + 1), sonst `null` |
| `veroeffentlicht` | bool oder `null` | wie bei `zuordnung/set`; `null` ohne Konfigurationsänderung |

**Zeiger:** Der Zeiger der Folge auf den Boxen (`resume.json`, je Serie und Folge)
gehört zur alten Serie. Die betroffenen Folgen-Tobies beginnen auf den Boxen nach dem
Sync **von vorn**. Das sagt die Seite in der Rückfrage (offener Punkt 3).

Reihenfolge der Schritte (Sperren nach Abschnitt 1: beide Serien nach Serien-ID, dann
Konfiguration): (1) Dateien in den Zielordner verschieben, (2) `serie.json` der
Zielserie schreiben, (3) `serie.json` der bisherigen Serie schreiben, (4) falls Tobies
betroffen: Konfiguration ändern, veröffentlichen, exportieren. Bricht es nach (1) ab,
findet die nächste Prüfung die Folge im Zielordner und trägt sie hinten ein; es geht
nichts verloren.

Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `ziel_ungueltig`,
`tobies_betroffen`, `stand_veraltet`, `konfig_nicht_bereit` (Tobies betroffen, aber
`konfig.zustand` nicht `ok`; dann wird nichts verschoben), `medien_schreibfehler`.
Recht: alltag (Ziel „Überraschungs-Serie“ nur für Administratoren, 2.4). Idempotent: Endzustand ja; der zweite Aufruf liefert
`folge_nicht_gefunden`. MQTT: `tobibox/config` (Revision + 1) nur bei betroffenen
Tobies.

#### 27. `tobibox/serien/zusammenfuehren`

Führt zwei Serien zu einer zusammen (Korrektur, Entscheidung M): Alle Folgen der
Quellserie gehen in die Zielserie, die Quellserie (dann leer) geht in den Papierkorb.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `quelle_id` | string | **ja** | diese Serie geht auf |
| `ziel_id` | string | **ja** | diese Serie bleibt. Beide müssen `typ="normal"` sein, sonst `ziel_ungueltig`; gleiche Serie: `ziel_ungueltig`. |
| `tobies_bestaetigt` | bool | nein | Vorgabe `false`. Zeigen Tobies auf die Quellserie oder eine ihrer Folgen, lehnt das Backend ohne `true` ab (`tobies_betroffen`). |
| `stand_quelle`, `stand_ziel` | string | nein im Schema, **die Seite muss sie senden** | |

Die Folgen der Quelle werden einzeln nach der Regel aus 11.6 in die Zielserie
eingefügt, mit Suffix bei Namensgleichheit (Abschnitt 12). Alle Tobies, die auf die
Quellserie zeigen (`serie` und `folge`), zeigen danach auf die Zielserie
(`ziel.serie` und gegebenenfalls `ziel.folge` werden umgeschrieben). Deren Zeiger auf
den Boxen beginnen von vorn (wie bei Nr. 26).

Ausgabe: `{"ziel": <Serie-Kurzform>, "verschoben": <int>, "umbenannt": [{"von", "nach"}…],
"betroffene_tobies": […], "eintrag": <Papierkorb-Eintrag der Quellserie>, "konfig": …,
"veroeffentlicht": …}` (wie bei Nr. 26). Fehler: wie Nr. 26 mit `serie_nicht_gefunden`.
Recht: admin. Idempotent: Endzustand ja; der zweite Aufruf liefert
`serie_nicht_gefunden`. MQTT: `tobibox/config` nur bei betroffenen Tobies.

#### 28. `tobibox/einsortierung/bestaetigen`

Nimmt das Kennzeichen „bitte prüfen“ (Abschnitt 11.9) weg: Tobias hat hingeschaut.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folgen` | array von string | nein | nur diese Folgen (Namen); ohne das Feld: die Serie selbst und alle ihre Folgen |

Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `serie_nicht_gefunden`,
`folge_nicht_gefunden`, `medien_schreibfehler`. Recht: alltag. Idempotent: ja.
MQTT: –. Auch `serie/rename`, `folge/rename` und `folge/verschieben` löschen das
Kennzeichen des Objekts, das sie ändern; `folgen/order` tut es nicht.

### 3.3 Papierkorb

**Papierkorb-Eintrag** (`eintrag`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | Kennung des Eintrags (12 Zeichen `[0-9a-f]`, vom Backend erzeugt) |
| `typ` | `folge`, `serie` oder `eingang` | was gelöscht wurde: eine Folge, eine ganze Serie oder etwas aus dem Eingang (Doppelte, Reste, Abschnitt 11.10) |
| `serie_id` | string oder `null` | Serie, aus der es kam (`null` bei `eingang`) |
| `serie_name` | string oder `null` | Name der Serie zum Zeitpunkt des Löschens |
| `folge` | string oder `null` | Name der Folge (bei `typ="folge"`) |
| `anzeige` | string | Anzeigename der Folge bzw. der Serie bzw. der Name im Eingang |
| `art` | `datei` oder `ordner` | |
| `tracks` | int | Anzahl Dateien |
| `groesse_bytes` | int | |
| `grund` | `manuell`, `zusammengefuehrt`, `doppelt`, `eingang_rest` | Wie es in den Papierkorb kam |
| `geloescht_am` | string | Zeitstempel |
| `geloescht_von` | object oder `null` | **(12.11.)** `{"id": <HA-Benutzerkennung>, "name": <Name aus Home Assistant>}`; `null` bei Einträgen von vor dem 12.11., aus dem Eingangs-Lauf oder von einer Aktion. Die Seite zeigt ihn nur Administratoren („gelöscht von …“). Er steht auch in `meta.json` (`data-model.md`, Abschnitt 9) |

Der Papierkorb liegt auf der Freigabe unter `medien/_papierkorb/`. Die Boxen
übernehmen ihn nicht (vom Sync ausgenommen). **Aufbau (W-18):** Je Eintrag ein Ordner
`_papierkorb/<id>/` mit der Datei `meta.json` (Herkunft, Reihenfolge, `folgen_info`;
Format in `data-model.md`, Abschnitt 9) und dem Ordner `inhalt/` mit dem Gelöschten
unter seinem ursprünglichen Namen. Weil die `<id>` der Ordner ist, kollidieren zwei
Löschungen gleichnamiger Folgen nie. Das Verschieben ist ein Umbenennen auf derselben
Freigabe (atomar); `restore` baut ausschließlich auf `meta.json` auf.

#### 10. `tobibox/papierkorb/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–200 | nein | Vorgabe 100 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>, "gesamt_bytes": <int>}`,
neueste zuerst. Fehler: `medien_nicht_erreichbar`. Recht: lesen. Idempotent: ja.
MQTT: –.

#### 11. `tobibox/papierkorb/restore`

Stellt einen Eintrag wieder her.

*   `typ="folge"`: Die Folge kommt an ihren Platz im Serien-Ordner zurück, **hinten**
    in `folgen` (die alte Position wird nicht gemerkt); `folgen_info` kommt aus
    `meta.json` zurück.
*   `typ="serie"`: Der Serien-Ordner kommt zurück (unter dem alten Ordnernamen, bei
    Namensgleichheit mit Suffix nach Abschnitt 12; die Serien-ID bleibt).
*   `typ="eingang"`: Es kommt in den Eingang zurück (oberste Ebene, bei Namensgleichheit
    mit Suffix) und wird beim nächsten Durchlauf wieder einsortiert.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | |
| `serie_id` | string | nein | nur bei `typ="folge"`: in diese Serie statt in die ursprüngliche wiederherstellen (wenn die ursprüngliche nicht mehr da ist) |

Ausgabe: `{"serie": <Serie-Kurzform oder null>, "folge": <Folge-Name oder null>}`
(`null` bei `typ="eingang"`). Fehler:
`eintrag_nicht_gefunden`, `serie_nicht_gefunden` (die Serie gibt es nicht mehr),
`serie_existiert` (`typ="serie"`: die Serien-ID ist schon vergeben),
`datei_existiert` (`typ="folge"`: im Serien-Ordner liegt inzwischen eine Folge mit
demselben Namen), `medien_schreibfehler`. Recht: admin. Idempotent: Endzustand ja; der
zweite Aufruf liefert `eintrag_nicht_gefunden`. MQTT: –. Nebenwirkung: Zuordnungen, die
auf die Folge oder Serie zeigten, gelten wieder, sobald die Box sie nach dem Sync hat.

#### 12. `tobibox/papierkorb/empty`

Löscht den Papierkorb **endgültig** (Knopf „Papierkorb leeren“; es gibt keine
Automatik).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf; die Seite fragt vorher nach. `false` oder fehlend: `invalid_format` |
| `eintrag_ids` | array von string | nein | nur diese Einträge; ohne das Feld: alle |

Ausgabe: `{"geloescht": <int>, "freigegeben_bytes": <int>}` (Platz auf der
Freigabe, **nicht** auf den Boxen). Fehler: `medien_schreibfehler` (ein Teil kann
schon gelöscht sein; `geloescht` steht dann in `message`, die Seite lädt neu).
Recht: admin. Idempotent: ja (leerer Papierkorb: `geloescht=0`). MQTT: –.

### 3.4 Neue Tobies (Weg A, CUJ 7a, 12)

**Seit 13.11. (3.13):** Wartet für die meldende Box eine passende Vormerkung der Warteschlange, ordnet das Backend den Tobie sofort zu. Die Kennung kommt dann gar nicht erst in diese Liste (kein `neu`, auch kein Feld an `neue_tobies/list`); die Bestätigung an die Box ist `bekannt`. Ohne passende Vormerkung gilt unverändert, was hier steht.

Das Backend führt die Liste **„Neue Tobies“** aus den Meldungen auf
`tobibox/<box>/unknown/<uid>` (`mqtt-v1.md`, 3.5): Eine Kennung, die **beide**
Boxen melden, ist **ein** Eintrag. Die Liste liegt im HA-Speicher (Teil der
HA-Sicherung), getrennt von der Konfiguration (keine Revision, nicht auf MQTT). Das
Backend bestätigt jede Meldung sofort auf `…/ack` (`neu`, bei bekannter Kennung
`bekannt`); die Box löscht daraufhin ihren Eintrag. „Bestätigen“ in der Oberfläche
heißt **zuordnen** (`zuordnung/set`); das `ack` an die Box geht automatisch und ist
kein Knopf (Vorgabe der Projektleitung 09.11.).

**`bekannt`** (W-11) heißt: Die Kennung steht **schon in der Liste „Neue Tobies“ oder
schon in den Zuordnungen**. Steht sie in den Zuordnungen (die Box war lange offline
und kannte die Zuordnung noch nicht, oder ein Tobie wurde gerade zugeordnet), nimmt das
Backend sie **nicht** in „Neue Tobies“ auf und bestätigt mit `bekannt`; in der Box-Liste
zeigt `konfig_stand="veraltet"` (3.7), dass diese Box die Liste noch nicht hat. Die
Liste in HA bleibt, bis Tobias die Kennung **zuordnet** (`zuordnung/set`, auch über den
Lernmodus) oder **verwirft**. Meldet eine Box die Kennung danach erneut (der Tobie
liegt wieder auf) und sie ist weder zugeordnet noch verworfen worden, erscheint sie
wieder; eine verworfene Kennung erscheint bei erneuter Meldung wieder.

**Eintrag „Neuer Tobie“:**

| Feld | Typ | Bedeutung |
|---|---|---|
| `uid` | string | Kennung |
| `zuerst` | string | früheste Meldung aller Boxen |
| `zuletzt` | string | späteste Meldung aller Boxen |
| `anzahl` | int | Summe über die Boxen von **`anzahl` der jeweils letzten Nachricht** dieser Box. Die Zahl in einer Nachricht ist schon die Summe der Box; das Backend **ersetzt** den Wert je Box und addiert nie bei jeder Nachricht. |
| `boxen` | object | je Box, die ihn gemeldet hat: `{"zuerst", "zuletzt", "anzahl", "zeit_ok"}` (Werte aus der Meldung; bei `zeit_ok=false` sind die Zeiten mit Vorsicht zu lesen) |

#### 13. `tobibox/neue_tobies/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–200 | nein | Vorgabe 100 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>}`, nach `zuletzt` absteigend.
Recht: lesen. Idempotent: ja. MQTT: –.

#### 14. `tobibox/neue_tobies/verwerfen`

Nimmt eine Kennung aus der Liste, ohne sie zuzuordnen.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | kanonische Kennung |

Ausgabe: `{"entfernt": <bool>}` (`false`: war nicht in der Liste). Fehler:
`kennung_ungueltig`. Recht: alltag. Idempotent: ja (zweimal: `entfernt=false`, kein
Fehler). MQTT: **keine** (die Bestätigung ging schon beim Eintreffen raus). Die Box
spielt für diesen Tobie weiter die Überraschungs-Serie.

### 3.5 Zuordnungen

#### 15. `tobibox/zuordnung/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | nein | nur Zuordnungen, die auf diese Serie zeigen (`serie` und `folge`) |
| `uid` | string | nein | **(09.11., AP 4.7, Erweiterung v1.1)** nur die Zuordnung dieser Kennung: `gesamt` ist 0 oder 1. Die Kennung wird so verglichen, wie sie gesendet wird (kanonisch, `reader-v1.md`, Abschnitt 4); eine unbekannte oder anders geschriebene Kennung ergibt eine leere Liste, keinen Fehler. Zusammen mit `serie_id` gilt „und“. Nur senden, wenn `hello.faehigkeiten` `zuordnung_uid` zusagt (Abschnitt 9). |
| `text` | string, 2–100 Zeichen | nein | **(12.11., Fähigkeit `bibliothek`)** Tobie-Name oder Ziel enthält den Text |
| `neu` | bool | nein | **(12.11., Fähigkeit `bibliothek`)** `true`: zuletzt angelegt zuerst (Sortierung nach `angelegt_am`) |
| `limit` | int 1–100 | nein | Vorgabe 100 (Vorgabe der Projektleitung 09.11., W-13) |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `konfig` | object | Konfig-Stand |
| `zuordnungen` | array | je Eintrag: `{"uid", "name" (oder null), "ziel", "angelegt_am" (12.11.: Zeitstempel oder fehlt), "serie_name" (oder null), "folge_anzeige" (oder null), "folge_vorhanden" (bool oder null), "vorher" (13.11., K6: object oder null), "cover_stand" (13.11., K8: string oder null)}`; `serie_name` ist `null`, wenn die Serie auf der Freigabe fehlt, `folge_vorhanden` und `folge_anzeige` nur bei `typ="folge"`. **`vorher` (13.11., K6):** `{"ziel": <Ziel, gleiche Form wie `ziel`>, "am": <Zeitstempel der Umstellung>}` oder `null`, wenn es keins gibt; das Feld steht **immer** da. Regeln siehe „`vorher`“ unten. |
| `gesamt` | int | Anzahl aller passenden Zuordnungen |

**`cover_stand` (13.11., K8):** der Cover-Stand der Serie, auf die das Ziel zeigt (`serie` und `folge`); `null` bei `gute_nacht`, `aktion`, fehlender Serie und Serien ohne Cover. Das Feld steht immer da.

Sortiert nach `uid`. Eine Seite hat höchstens 100 Einträge (≈ 35 KiB, unter der
Grenze von 64 KiB, Abschnitt 8; mit `vorher` bis etwa 45 KiB). Recht: lesen. Idempotent: ja. MQTT: –.

**`vorher` (13.11., K6).** Das Backend merkt sich je Kennung das Ziel vor der letzten Umstellung, damit die Zeile „Vorher: … · Zurückstellen“ (Design 5.4, R17-3) auf jedem Gerät steht. Die Seite blendet sie nach 24 Stunden aus (`am`); das Backend löscht nichts nach Zeit.
1.  **Gesetzt** wird `vorher`, wenn eine **bestehende** Zuordnung ein **anderes** Ziel bekommt (`zuordnung/set`, ebenso der Lernmodus beim Umhängen, 3.6): `ziel` = das alte Ziel, `am` = jetzt. Wird ein schon umgehängter Tobie noch einmal auf ein drittes Ziel umgestellt, ersetzt das neue `vorher` das alte.
2.  **Beim Neuanlegen** (die Kennung hatte keine Zuordnung, auch über die Warteschlange, 3.13) ist `vorher` `null`.
3.  **Zurückstellen / Rückgängig:** Bekommt die Kennung das Ziel zurück, das in `vorher` steht, wird `vorher` wieder `null`. Das ist die Wirkung von „Zurückstellen“ und „Rückgängig“ im Design (5.4, R17-3: dieselben Befehle, `zuordnung/set` mit dem alten Ziel und `erwartet_ziel`); die Seite braucht keinen eigenen Befehl. Ändert sich nur der Name oder bleibt das Ziel gleich (`geaendert=false`), bleibt `vorher` wie es ist.
4.  **Entfernt** (`zuordnung/remove`) oder ersetzt (Liste neu ausgerollt, aus Export eingespielt, 13): kein `vorher`.
5.  **Speicher:** nur im HA-Speicher, **nicht** in der Konfiguration. Zuordnung und `vorher` gehen **in einem Schreibvorgang** (nach einem Absturz gilt beides oder nichts). `vorher` ändert die Revision nicht und geht nie auf MQTT, in den Export oder zur Box; die Box bekommt die Zuordnungsliste ohne das Feld (`mqtt-v1.md` und `data-model.md` bleiben unverändert).

#### 16. `tobibox/zuordnung/set`

Ordnet eine Kennung einem Ziel zu (Typ `serie`, `folge` oder `aktion`, Entscheidung F)
und gibt ihr optional einen **Namen**. Das ist der Weg für „Neue Tobies“, für
Aktionskarten (Status, Gute Nacht) und für Kennungen, die Tobias von Hand eingibt.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | kanonische Kennung (`reader-v1.md`, Abschnitt 4) |
| `ziel` | object | **ja** | Ziel, siehe oben |
| `name` | string, 1–60 Zeichen, oder `null` | nein | Tobie-Name (Vorgabe der Projektleitung 09.11.; `data-model.md`, Abschnitt 2). Fehlt das Feld, bleibt ein vorhandener Name unverändert; `null` löscht ihn. Steuerzeichen werden entfernt, Leerraum gekürzt; danach leer: `name_ungueltig`. Die Box ignoriert den Namen. |
| `ueberschreiben` | bool | nein | Vorgabe `false`. Hat die Kennung schon **ein anderes** Ziel, antwortet das Backend ohne `ueberschreiben=true` mit `zuordnung_existiert`; die Seite fragt Tobias und sendet erneut mit `true`. |
| `erwartet_ziel` | object oder `null` | nein | Das Ziel, das die Seite zuletzt gesehen hat (`null`: „keine Zuordnung“). Stimmt es nicht mit dem Stand im Backend überein, lehnt das Backend ab (`zuordnung_geaendert`, W-12), und die Seite lädt `zuordnung/list` neu. Ist `erwartet_ziel` gesetzt, entfällt die Prüfung auf `ueberschreiben`. Fehlt es, gilt „letzter Schreiber gewinnt“ (nur für Aktionen und Automationen und **nur für Administratoren**; **seit 12.11. ist es für Nicht-Administratoren Pflicht**, sonst `unauthorized`, 2.4). **Die Seite sendet es immer.** |

Prüfung: `ziel.typ` ∈ `serie`, `folge`, `aktion`; bei `serie`/`folge` muss die Serie in
der Medienverwaltung existieren (`serie_nicht_gefunden`; sie muss **nicht** schon auf
einer Box sein, das Design erlaubt das, die Box spielt bis dahin die
Überraschungs-Serie); **die Überraschungs-Serie ist als Ziel verboten**
(`ziel_ungueltig`, Vorgabe der Projektleitung 09.11.); bei `folge` muss die Folge in
`folgen` stehen (`folge_nicht_gefunden`); bei `aktion` ist nur `status` oder
`gute_nacht` erlaubt (`ziel_ungueltig`).

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `geaendert` | bool | `false`, wenn die Kennung schon genau dieses Ziel **und** diesen Namen hatte (dann **keine** neue Revision, keine MQTT-Nachricht) |
| `konfig` | object | Konfig-Stand nach dem Befehl |
| `veroeffentlicht` | bool oder `null` | `tobibox/config` ist beim Broker angekommen (PUBACK); `false` heißt: gespeichert, wird nachgeholt; `null` bei `geaendert=false` (es gab keine Veröffentlichung, W-20) |

Fehler: `kennung_ungueltig`, `ziel_ungueltig`, `serie_nicht_gefunden`,
`folge_nicht_gefunden`, `zuordnung_existiert`, `zuordnung_geaendert`, `name_ungueltig`,
`konfig_zu_gross`, `konfig_nicht_bereit`. Recht: alltag.
Idempotent: **ja** (gleiches Ziel und gleicher Name zweimal: zweites Mal `geaendert=false`).
MQTT: veröffentlicht `tobibox/config` (retained, Revision + 1, `erzeugt_am` jetzt). Die
Boxen übernehmen nach der Revisionsregel (`mqtt-v1.md`, 5.2); liegt der Tobie gerade
auf, wechselt die Box auf das neue Ziel (`mqtt-v1.md`, 4.1, Schritt 6). Nebenwirkung:
Steht die Kennung in „Neue Tobies“, wird sie dort entfernt (Ereignis `neue_tobies`,
`art="entfernt"`, `grund="zugeordnet"`). Das Backend schreibt `leise_zeiten`,
`gute_nacht`, `ton_pegel`, `hinweis_pegel` und `lesezeichen_tage` unverändert fort
(Entscheidung N, 09.11.). **(09.11., Befund AP 3.1)** `lesezeichen_tage` legt das Backend selbst
an (Vorgabe 14) und veröffentlicht es in jeder `tobibox/config`; ein älterer Speicher ohne das Feld
bekommt 14.

#### 17. `tobibox/zuordnung/remove`

Löst eine Zuordnung („lösen“, Design: Aktionen). Der Tobie-Name geht mit.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `uid` | string | **ja** | |
| `erwartet_ziel` | object | nein | wie bei `zuordnung/set` (W-12); Abweichung: `zuordnung_geaendert`. **Seit 12.11. für Nicht-Administratoren Pflicht** (sonst `unauthorized`, 2.4). **Die Seite sendet es immer.** |
| `als_neu` | object `{"box": <string>}` | nein | **(13.11., Fähigkeit `zuordnung_rueckgaengig`)** Nur für „Rückgängig“ nach dem Zuordnen eines **neuen** Tobies (X20d). Wurde etwas entfernt (`geaendert=true`), nimmt das Backend die Kennung als neuen Tobie wieder in „Neue Tobies“ auf: Ereignis `neue_tobies` `neu`, `boxen.<box>` mit `zuerst` = `zuletzt` = jetzt (Wanduhr von HA), `anzahl` 1, `zeit_ok` `true`. Die Box bekommt keine Nachricht; meldet sie den Tobie später selbst, gilt die Meldung als `aktualisiert`. Bei `geaendert=false` geschieht nichts. Unbekannte Box: `box_unbekannt`. Ohne das Feld bleibt alles wie bisher: Der Tobie erscheint erst wieder, wenn er erneut aufgelegt wird. |

Ausgabe: wie `zuordnung/set` (`geaendert=false` und `veroeffentlicht=null`, wenn es
keine Zuordnung gab). Fehler: `kennung_ungueltig`, `zuordnung_geaendert`,
`konfig_nicht_bereit`, `box_unbekannt` (nur mit `als_neu`, 13.11.). Recht: alltag. Idempotent: ja. MQTT: veröffentlicht
`tobibox/config` (Revision + 1), wenn etwas entfernt wurde. Danach spielt die Box
für den Tobie die Überraschungs-Serie und meldet ihn beim nächsten Auflegen als
unbekannt; er erscheint wieder in „Neue Tobies“.

**„Rückgängig“ nach dem Zuordnen (X20d, 13.11.).** Die Seite braucht dafür keinen eigenen Befehl, aber für einen Fall ein zusätzliches Feld:
*   **Der Tobie hatte schon ein Ziel** (Umstellen): `zuordnung/set` mit dem **alten** Ziel (und dem alten `name`, oder `null`, wenn er keinen hatte) und `erwartet_ziel` = dem Ziel, das die Seite gerade gesetzt hat. Das schützt vor dem Überschreiben, wenn inzwischen jemand anderes etwas geändert hat (`zuordnung_geaendert`). Nichts Neues nötig.
*   **Der Tobie war neu** (Weg 1 oder Warteschlange): `zuordnung/remove` mit `erwartet_ziel` = dem gerade gesetzten Ziel genügt für die Konfiguration. Damit die Karte „Neuer Tobie auf Box 1“ (Design 7.1) **sofort** wiederkommt, sendet die Seite zusätzlich `als_neu` mit der Box, auf der er lag. Das Feld ist die einzige Neuerung. *(Lücke im Design: Es verspricht „der Tobie liegt wieder als unbekannter da“, der Vertrag kannte dafür bisher nichts. Ohne `als_neu` erschiene die Karte erst beim nächsten Auflegen.)* Beide Wege zählen als Änderung der Liste (Menge, 2.4).

### 3.6 Lernmodus (Weg B, CUJ 7b)

Ablauf und Reihenfolge: Abschnitt 6.2. Hier die Befehle. **Seit 13.11. (X13a) sind alle drei Befehle nur für Administratoren** (`@websocket_api.require_admin`, Fehler `unauthorized`); im Alltag ersetzt sie die Warteschlange (3.13).

#### 18. `tobibox/lernmodus/start`

„Jetzt kommt ein neuer Tobie“: Das Backend merkt sich Box, Ziel und Beginn und sendet
den Befehl `lernen` an die Box (`mqtt-v1.md`, 3.7 und 4.2).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | Box-Name |
| `ziel` | object | **ja** | nur `typ` `serie` oder `folge` (Aktionskarten gehen nicht über den Lernmodus, `mqtt-v1.md`, 3.8); die Überraschungs-Serie ist verboten (`ziel_ungueltig`) |
| `name` | string, 1–60 Zeichen | nein | Tobie-Name, der bei der Zuordnung gesetzt wird (wie bei `zuordnung/set`) |
| `anfrage_id` | string | nein | siehe 2.2 |

Prüfung wie bei `zuordnung/set` (Serie und Folge müssen existieren). Die Box muss
`online` sein; ist `online` `null` (HA kennt noch keine Nachricht), gilt sie als
offline (`box_offline`, W-25). Ist `konfig.zustand` nicht `ok`: `konfig_nicht_bereit`.

Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `befehl_id` | string | `id` des Befehls `lernen` (UUID); kommt in den Ereignissen und bei `lernmodus/antwort` wieder vor |
| `box` | string | |
| `ziel` | object | |
| `beginn` | string | Zeitstempel (Wanduhr von HA) |
| `frist_bis` | string | bis wann das Backend die Meldung dieses Befehls annimmt: `beginn` + 180 s (60 s Lebensdauer des Befehls + 120 s Lernfrist der Box) |

Fehler: `box_unbekannt`, `box_offline`, `mqtt_nicht_verbunden`, `ziel_ungueltig`,
`serie_nicht_gefunden`, `folge_nicht_gefunden`, `name_ungueltig`, `konfig_nicht_bereit`,
`lernmodus_laeuft` (für diese Box läuft schon ein **lebender** Vorgang mit **anderem**
Ziel: **erst abbrechen**, Vorgabe der Projektleitung 09.11.; mit gleichem Ziel antwortet
das Backend mit dem laufenden Vorgang, siehe unten), `anfrage_id_konflikt`. Recht: admin (seit 13.11.; vorher alltag). MQTT: `tobibox/<box>/cmd` mit `befehl="lernen"`, `ttl_s` 60, `daten` `{}`. Das
Ziel geht **nicht** an die Box. Lehnt die Box den Befehl ab (`event`
`befehl_abgelehnt`, z. B. `zeit_unsicher`), meldet das Backend es als Ereignis
`lernmodus` mit `zustand="box_lehnt_ab"` (mit Klartext, `mqtt-v1.md`, 3.4).

**Idempotenz und „lebender“ Vorgang (W-05).** Ein Vorgang ist **lebendig**, solange er
weder beendet ist noch als tot gilt. Er gilt als **tot**, wenn (a) ein Status der Box
mit `lernmodus=true` für diesen Vorgang gesehen wurde und danach ein Status mit
`lernmodus=false` eintraf, oder (b) `frist_bis` vorbei ist, oder (c) seit `beginn` mehr
als 30 s vergangen sind, ohne dass je ein Status mit `lernmodus=true` eintraf. Ein toter
Vorgang endet mit dem Zustand `abgelaufen` (Ereignis `lernmodus`). Beim Start mit
gleicher Box und **gleichem** Ziel liefert das Backend nur einen **lebenden** Vorgang
unverändert zurück (kein zweiter Befehl); ist der Vorgang tot oder gibt es keinen,
beginnt ein neuer mit neuem Befehl. Bei **anderem** Ziel gilt `lernmodus_laeuft` nur
für einen lebenden Vorgang. Ohne `anfrage_id` ist der Befehl sonst nicht idempotent;
deshalb `anfrage_id`.

#### 19. `tobibox/lernmodus/antwort`

Antwort auf die **Rückfrage vor dem Überschreiben** (Ereignis `lernmodus` mit
`zustand="rueckfrage"`, 6.2).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `befehl_id` | string | **ja** | aus dem Ereignis |
| `ueberschreiben` | bool | **ja** | `true`: die bestehende Zuordnung wird durch das Ziel des Lernmodus ersetzt. `false`: bleibt, das Backend lehnt die Meldung ab. |

Ausgabe: `{"zustand": "zugeordnet" | "abgelehnt", "konfig": <Konfig-Stand>}`.
Fehler: `kein_lernmodus` (kein offener Vorgang mit dieser `befehl_id`),
`rueckfrage_abgelaufen` (die Frist `rueckfrage_bis` ist vorbei, das Backend hat schon
mit `abgelehnt` bestätigt). Recht: admin (seit 13.11.; vorher alltag). Idempotent: Endzustand ja; eine zweite
Antwort liefert `kein_lernmodus`. MQTT: bei `true` zuerst `tobibox/config` (Revision
+ 1), **danach** `…/ack` mit `grund="zugeordnet"` (erst nach dem PUBACK, 6.2 Schritt 4);
bei `false` nur `…/ack` mit `grund="abgelehnt"` (keine neue Konfiguration). Beide `ack`
tragen `zuletzt` und `art` der gemeldeten Kennung (`mqtt-v1.md`, 3.6).

#### 20. `tobibox/lernmodus/abbrechen`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |

Ausgabe: `{"abgebrochen": <bool>}` (`true`, wenn ein Vorgang offen war). Das Backend
verwirft den Vorgang und sendet immer `lernen_abbrechen`, auch ohne offenen Vorgang
(im Zustand „Lernmodus aus“ wirkungslos, `mqtt-v1.md`, 3.7). Eine Meldung, die danach
noch mit der `befehl_id` des verworfenen Vorgangs eintrifft, bestätigt das Backend
mit `grund="abgelehnt"` (die Box meldet den Tobie dann erneut als unbekannt).
**Steht eine Rückfrage offen** (die Meldung ist schon eingetroffen), sendet das Backend
das `ack` mit `grund="abgelehnt"` **sofort beim Abbrechen** (W-24); die Box wartet
nicht auf die Frist.

Fehler: `box_unbekannt`, `mqtt_nicht_verbunden`. Kein `box_offline`: Der Abbruch
wird auch an eine Box gesendet, die gerade nicht antwortet (Lebensdauer 30 s).
Recht: admin (seit 13.11.; vorher alltag). Idempotent: ja. MQTT: `tobibox/<box>/cmd` mit
`befehl="lernen_abbrechen"`, `ttl_s` 30. Das Ereignis `lernmodus` meldet
`zustand="abgebrochen"`.

### 3.7 Boxen

#### 21. `tobibox/boxen/list`

Keine Eingabe. Ausgabe: `{"boxen": [<Box>…]}`, in der Reihenfolge der Einrichtung.

**Box-Objekt:**

| Feld | Typ | Bedeutung |
|---|---|---|
| `box` | string | Box-Name |
| `anzeigename` | string oder `null` | Gerätename aus der Discovery (`Tobi Box <anzeigename>`), `null`, wenn die Box noch nie da war |
| `online` | bool oder `null` | aus `tobibox/<box>/online` (`online`/`offline`); `null`, wenn HA noch keine Nachricht kennt (für Befehle wie `offline`, `box_offline`) |
| `status` | object oder `null` | der letzte `tobibox/<box>/status` **unverändert** (`mqtt-v1.md`, 3.3, mit `speicher_frei_mb`, `netz`, `akku_prozent`, `sync`, `version`, `letzter_fehler`, `konfig`, `update` …); `null` ohne Nachricht. Neue Statusfelder erscheinen hier ohne Vertragsänderung. |
| `status_empfangen_am` | string oder `null` | wann HA ihn empfangen hat |
| `konfig_stand` | `aktuell`, `veraltet`, `voraus`, `unbekannt` | `status.konfig` gegen den Stand in HA (W-02): `aktuell` = gleiche `liste_id` und `revision`; `veraltet` = andere `liste_id` oder niedrigere `revision` als in HA; **`voraus` = gleiche `liste_id` und `revision` der Box höher als in HA** (typisch nach dem Zurückspielen einer Sicherung, Abschnitt 13); `unbekannt` ohne Status |
| `anzeige` | string | **(12.11.)** Anzeigename der Box für die Seite (nie `null`; 14.9) |
| `lernmodus` | object oder `null` | der offene Vorgang dieser Box (Felder wie im Ereignis `lernmodus`, 4.3), sonst `null` |
| `ereignisse` | array | **(seit 12.11. nur für Administratoren; für andere fehlt das Feld)** die letzten **20** Meldungen von `tobibox/<box>/event` (neueste zuerst), **im HA-Speicher** und damit über einen Neustart hinaus (Vorgabe der Projektleitung 09.11.): `{"id", "ts", "art", "daten", "text"}`; `art` und `daten` unverändert (`liste_abgelehnt`, `fehler`, `befehl_abgelehnt`), `text` ist der Klartext des Backends (`mqtt-v1.md`, 3.4: „Die Box … hat … abgelehnt“). So sieht Tobias abgelehnte Listen. |

Recht: lesen (das Feld `ereignisse` nur für Administratoren, 2.1). Idempotent: ja. MQTT: –. Fehler: keine.

#### 22. `tobibox/box/sync`

Stößt den Medien-Sync der Box an (CUJ 9: „von HA angestoßen“). Ob er läuft, entscheidet
die Box nach der Netz-Regel (Heimnetz immer; Hotspot nur mit Lader oder über 50 %; „Lader“ = Strom am Eingang aus jeder Quelle, Ein/Aus, 10.11.); wenn nicht,
steht es im Status (`sync.ergebnis="abgebrochen"`, `grund`). Der Sync übernimmt weder
`_upload/` noch `_papierkorb/` noch den Eingang (Abschnitt 11.1).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string | **ja** | |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"befehl_id": <string>, "ttl_s": 300}`. Fehler: `box_unbekannt`,
`box_offline` (auch bei `online=null`), `mqtt_nicht_verbunden`, `anfrage_id_konflikt`.
Recht: admin. Idempotent: nicht ohne `anfrage_id`; ein zweiter Sync-Befehl während
eines Syncs ist für die Box harmlos (sie startet keinen zweiten). MQTT:
`tobibox/<box>/cmd`, `befehl="sync"`, `ttl_s` 300, `daten` `{}`. Das Ergebnis kommt über
den Status (Ereignis `boxen`).

### 3.8 Liste

#### 23. `tobibox/liste/neu_ausrollen`

Erzeugt eine neue Listen-ID und veröffentlicht die Konfiguration neu. Alle Boxen
nehmen sie an, auch bei niedrigerer Revision (`mqtt-v1.md`, 5.1 und 5.3; Betriebshandbuch
für den Fall einer Wiederherstellung aus der Sicherung). Der Befehl ist in **jedem**
Zustand der Konfiguration erlaubt (Abschnitt 13) und ist der Weg heraus aus `leer_neu`
(„mit leerer Liste neu beginnen“) und aus `export_neuer` („den Stand in HA behalten“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf. Die Seite zeigt vorher, was passiert: bei `leer_neu` „Alle Tobies verlieren ihre Zuordnung“. |
| `anfrage_id` | string | nein | siehe 2.2 |

Ausgabe: `{"konfig": <Konfig-Stand>, "veroeffentlicht": <bool>}`. Die neue Liste
beginnt mit Revision 1 (`data-model.md`, Abschnitt 2) und `zustand="ok"`. Fehler:
`anfrage_id_konflikt`. Recht: admin. Idempotent: **nein** (jeder Aufruf erzeugt eine neue
Listen-ID; harmlos, aber unnötig), deshalb `anfrage_id`. MQTT: `tobibox/config` mit
neuer `liste_id`, `revision` 1, gleiche Zuordnungen und Einstellungen wie der
HA-Speicher (bei `leer_neu`: leer). Der Export auf das NAS läuft danach im Hintergrund
wie nach jeder Änderung.

### 3.9 Eingang (Entscheidung M)

Tobias legt Hörbücher und Hörspiele in den **Eingang** (`tobibox/eingang/` auf dem NAS,
Abschnitt 11.1). Die Integration liest die Tags und sortiert **automatisch** in die
Medienstruktur ein (Regeln: Abschnitt 11). Die Seite zeigt, was im Eingang liegt und
was erkannt wurde, und Tobias korrigiert mit den Befehlen Nr. 6, 7, 25, 26, 27
und 28.

**Eingangs-Eintrag** (`eintrag`): ein Eintrag der **obersten Ebene** von `eingang/`
(eine Datei oder ein Ordner).

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string | 12 Zeichen `[0-9a-f]`: Anfang der SHA-256 des Namens (stabil über Durchläufe) |
| `name` | string | Name der Datei oder des Ordners |
| `art` | `datei` oder `ordner` | |
| `dateien` | int | Anzahl Audiodateien darin (Endungsliste, ohne Dotfiles) |
| `ignoriert` | int | Anzahl anderer Dateien (Bilder, Texte …), die nie einsortiert werden |
| `groesse_bytes` | int | Summe der Audiodateien |
| `zuerst_gesehen` | string | wann ein Durchlauf den Eintrag zum ersten Mal sah (daraus die Eingangsreihenfolge, 11.6) |
| `geaendert_am` | string | neueste Änderungszeit darin |
| `status` | string | `wartet` (Ruhezeit läuft: zuletzt vor weniger als 120 s geändert), `bereit` (kommt beim nächsten Durchlauf dran), `laeuft`, `blockiert` (nichts davon einsortiert, siehe `hinweise`), `teilweise` (ein Teil einsortiert, der Rest blockiert), `erledigt` (nur mit Filter `erledigt`: aus dem Protokoll) |
| `hinweise` | array | `{"code", "datei", "text"}`: `kopierschutz`, `nicht_lesbar`, `probedekodierung_fehlgeschlagen`, `ffprobe_fehlt`, `keine_audiodateien`, `verschieben_fehlgeschlagen`, `doppelt` (die Datei war schon vorhanden und kam in den Papierkorb), `vorgabe_serie_fehlt`, `gruppe_unvollstaendig` (12.11., 14.4); `datei` ist der Pfad im Eintrag oder `null` |
| `ergebnis` | array | was einsortiert wurde: `{"serie_id", "serie_name", "serie_neu" (bool), "folge" (Name), "anzeige", "tracks", "pruefen" (bool), "pruefen_gruende" (array)}` |
| `fertig_am` | string oder `null` | wann der Eintrag (ganz oder teilweise) einsortiert wurde |
| `quelle` | `upload` oder `nas` | **(12.11.)** woher der Eintrag kam; fest, die Integration weiß es |
| `wunsch` | object oder `null` | **(12.11.)** `{"ziel", "art"}` des Upload-Wunsches (14.4); `null` ohne Wunsch |
| `pruefen` | bool | **(12.11.)** mindestens ein Element von `ergebnis` hat `pruefen=true` |

#### 29. `tobibox/eingang/list`

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `filter` | `offen`, `erledigt` oder `alle` | nein | Vorgabe `offen`: was noch im Eingang liegt (`wartet`, `bereit`, `laeuft`, `blockiert`, `teilweise`). `erledigt`: die letzten 100 einsortierten Einträge aus dem **Protokoll** im HA-Speicher (überlebt einen Neustart; älteres fällt heraus). |
| `limit` | int 1–100 | nein | Vorgabe 50 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `{"eintraege": [<Eintrag>…], "gesamt": <int>, "sortierung_laeuft": <bool>,
"geprueft_am": <string oder null>}`. Neueste zuerst (`zuerst_gesehen` absteigend). Die
Antwort kommt aus dem Zwischenspeicher des letzten Durchlaufs. Fehler:
`medien_nicht_erreichbar` (nur, wenn noch nie geprüft wurde). Recht: lesen.
Idempotent: ja. MQTT: –.

#### 30. `tobibox/eingang/sortieren`

Stößt einen Durchlauf des Einsortierens an („erneut einsortieren“): Einträge, die
blockiert waren (Tags nachgetragen, Datei ersetzt), und Einträge, die erst jetzt ruhig
sind. Beim Öffnen der Seite ruft die Seite `medien/pruefen` und `eingang/sortieren`
auf; der 10-min-Timer tut dasselbe.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_ids` | array von string | nein | nur diese Einträge; ohne das Feld: alle |
| `sofort` | bool | nein | Vorgabe `false`. `true` übergeht die Ruhezeit von 120 s (Tobias weiß, dass das Kopieren fertig ist). **Seit 12.11. nur für Administratoren** (sonst `unauthorized`, 2.4). |

Ausgabe: `{"gestartet": <bool>, "laeuft_bereits": <bool>, "eintraege": <int>}`
(`eintraege`: wie viele Einträge dieser Durchlauf bearbeitet). Der Durchlauf läuft im
Hintergrund; sein Ende kommt als Ereignis `eingang` (`durchlauf_fertig`), jeder
einsortierte Eintrag als `neu_einsortiert` (4.5). Läuft schon ein Durchlauf, meldet der
Befehl `laeuft_bereits=true`; die angegebenen Einträge werden im nächsten Durchlauf
bearbeitet. Fehler: `medien_nicht_erreichbar`, `eintrag_nicht_gefunden` (eine
`eintrag_id` unbekannt). Recht: alltag (mit `sofort` nur für Administratoren, 2.4). Idempotent: ja. MQTT: –.

#### 33. `tobibox/eingang/entfernen`

**(09.11., AP 4.7, Erweiterung v1.1.)** Legt einen Eintrag der obersten Ebene von `eingang/` in den
Papierkorb (`typ="eingang"`, `grund="manuell"`, Abschnitt 3.3). Gedacht für Blockiertes und Defektes
(Kopierschutz, nicht lesbar, keine Audiodateien), das Tobias sonst von Hand auf der Freigabe löschen müsste.
Der Eintrag lässt sich mit `papierkorb/restore` in den Eingang zurückholen.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | `id` des Eintrags aus `eingang/list` |
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf; die Seite fragt vorher nach. `false` oder fehlend: `invalid_format` |

Ausgabe: `{"eintrag": <Papierkorb-Eintrag>}` (3.3). Fehler: `eintrag_nicht_gefunden` (unbekannte `id`, oder der
Eintrag liegt nicht mehr im Eingang), `sortierung_laeuft` (ein Durchlauf des Einsortierens läuft; er kann Dateien
des Eintrags gerade bearbeiten, die Seite wiederholt später), `medien_nicht_erreichbar`, `medien_schreibfehler`.
Recht: admin. Idempotent: Endzustand ja; der zweite Aufruf liefert `eintrag_nicht_gefunden`. MQTT: –.
Nebenwirkungen: Ereignisse `eingang`/`geaendert` und `medien`/`papierkorb_geaendert`; die
HA-Benachrichtigung zu diesem Eintrag (4.5) wird entfernt. Fähigkeit `eingang_entfernen`. Die Seite zeigt den
Knopf nur bei `blockiert` und `teilweise`, mit Rückfrage.

### 3.10 Konfiguration: Sicherungsnetz (W-01, W-02)

Abschnitt 13 beschreibt die Zustände. Hier die beiden Befehle.

#### 31. `tobibox/konfig/export_lesen`

**(12.11.)** Recht seit 12.11. admin (vorher lesen). Neue optionale Eingabe `stand` und Ausgabe `staende`: 2.4, Fähigkeit `konfig_staende`. `konfig/aus_export` (Nr. 32) bekommt dieselbe Eingabe `stand`.

Zeigt, was im neuesten Export `export/config.json` auf dem NAS steht, ohne etwas zu
ändern.

Keine Eingabe. Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `vorhanden` | bool | es gibt eine lesbare Exportdatei |
| `liste_id`, `revision` | string, int | aus der Datei (sonst `null`) |
| `exportiert_am` | string oder `null` | `exportiert_am` aus der Datei |
| `anzahl_zuordnungen` | int oder `null` | |
| `anzahl_fenster` | int oder `null` | Leise-Zeiten-Fenster (Anzeige) |
| `neuer_als_ha` | bool | der Export ist neuer als der HA-Speicher (Abschnitt 13.2) |
| `konfig` | object | Konfig-Stand von HA zum Vergleich |

Fehler: `medien_nicht_erreichbar`, `export_ungueltig` (Datei da, aber nicht lesbar oder
nicht gültig nach `data-model.md`; `vorhanden` ist dann `false`, kein Fehler: der Code
gilt nur, wenn die Prüfung selbst scheitert). Recht: admin. Idempotent: ja. MQTT: –.

#### 32. `tobibox/konfig/aus_export`

Holt die Konfiguration aus dem Export zurück (Zuordnungen **mit Tobie-Namen**,
Leise-Zeiten, Gute-Nacht-Einstellungen, `ton_pegel`, `hinweis_pegel`, `lesezeichen_tage`) und verteilt
sie mit **neuer Listen-ID** und Revision 1 (damit keine Box sie wegen einer niedrigeren
Revision ablehnt). Erlaubt in jedem Zustand; Weg heraus aus `leer_neu` und
`export_neuer`.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `bestaetigt` | bool, muss `true` sein | **ja** | Schutz gegen versehentlichen Aufruf. Die Seite zeigt vorher das Ergebnis von `export_lesen` (Revision, Zeit, Anzahl Zuordnungen). |
| `anfrage_id` | string | nein | siehe 2.2 |

Das Backend prüft die Datei mit derselben Prüfung wie die Box (Migration und Schema,
`data-model.md`, Abschnitt 2); ist irgendein Teil ungültig, übernimmt es **nichts**
(`export_ungueltig`). Verweist eine Zuordnung auf eine Serie, die es nicht (mehr) gibt,
wird sie trotzdem übernommen (Zuordnung vor Medien ist erlaubt).

Ausgabe: `{"konfig": <Konfig-Stand>, "veroeffentlicht": <bool>, "uebernommen":
{"zuordnungen": <int>, "fenster": <int>}}`. Fehler: `export_nicht_gefunden`,
`export_ungueltig`, `medien_nicht_erreichbar`, `anfrage_id_konflikt`. Recht: admin.
Idempotent: **nein** (jeder Aufruf erzeugt eine neue Listen-ID), deshalb `anfrage_id`.
MQTT: `tobibox/config` mit neuer `liste_id`, `revision` 1.

#### 34. `tobibox/konfig/get`

**(09.11., AP 4.7, Erweiterung v1.1.)** Liest nur den Konfig-Stand, ohne `hello` und ohne eine Liste.
Keine Eingabe. Ausgabe: `{"konfig": <Konfig-Stand>}`, in jedem Zustand (bei `leer_neu` sind `revision` und
`liste_id` `null`). Fehler: keine außer den allgemeinen. Recht: lesen. Idempotent: ja. MQTT: –. Fähigkeit
`konfig_lesen`. Die Seite benutzt ihn, wenn sie nur den Stand neu lesen will (zum Beispiel nach
`konfig_nicht_bereit`); sonst bleibt es bei `hello`.

### 3.11 Einstellungen (AP 4.7)

Leise-Zeiten, Gute-Nacht-Dauern und der Ablauf der Lesezeichen (Entscheidung N) sind Teile der Konfiguration
(`config.json`, `data-model.md`, Abschnitt 2). Die Seite stellt sie hier ein; jede Änderung ist eine Änderung der
Konfiguration (Revision + 1, `tobibox/config`, Export; Abschnitt 1).

#### 35. `tobibox/einstellungen/get`

Keine Eingabe. Ausgabe:

| Feld | Typ | Bedeutung |
|---|---|---|
| `leise_zeiten` | object | `{"zeitzone": <IANA-Name>, "fenster": [<Fenster>…]}`; ein Fenster ist `{"id", "tage", "von", "bis", "wirkung", "grenze"}` wie in `data-model.md`, Abschnitt 2 (`grenze` nur bei `wirkung="leiser"`) |
| `gute_nacht` | object | `{"timer_min": <int 1–240>, "ausblenden_s": <int 5–600>}` |
| `lesezeichen_tage` | int 0–365 | `0` = nie; Vorgabe 14 (Entscheidung N) |
| `hinweis_pegel` | int 0–100 | nur, wenn die Konfiguration das Feld hat. Die Seite zeigt es nicht; `einstellungen/set` ändert es nicht. |
| `konfig` | object | Konfig-Stand |

Fehler: `konfig_nicht_bereit`, wenn der HA-Speicher keine Konfiguration hat (Zustand `leer_neu` nach einem
verlorenen Speicher; dann gibt es nichts zu zeigen, Abschnitt 13). In den übrigen Zuständen kann gelesen werden.
Recht: lesen. Idempotent: ja. MQTT: –. Fähigkeit `einstellungen`.

#### 36. `tobibox/einstellungen/set`

Setzt Einstellungen. **Mindestens ein** Feld ist Pflicht; ohne ein Feld und bei unbekannten Feldern (auch
`hinweis_pegel`) antwortet HA mit `invalid_format`.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `leise_zeiten` | object | nein | **ganzes Objekt** (`zeitzone` und `fenster`), ersetzt die bisherigen Leise-Zeiten. Ein Fenster, das fehlt, ist gelöscht. |
| `gute_nacht` | object | nein | **ganzes Objekt**: `timer_min` und `ausblenden_s` |
| `lesezeichen_tage` | int | nein | ganze Zahl 0 bis 365, `0` = nie; nur Administratoren (2.4) |
| `erwartet_revision` | int | nein | **(12.11., Fähigkeit `bibliothek`)** `konfig.revision`, die die Seite zuletzt gesehen hat; stimmt sie nicht, Fehler `stand_veraltet` und nichts wird geändert. Zählt nicht als „Änderung“ im Sinn von „mindestens ein Feld“. Für Nicht-Administratoren wird `leise_zeiten.zeitzone` ignoriert (der gespeicherte Wert bleibt, 2.4) |

**Prüfung: genau die der Box** (`box/src/tobibox/store.py`, `parse_konfig`; in HA `store.pruefe_leise_zeiten`,
`pruefe_gute_nacht`, `pruefe_lesezeichen_tage`, die auch Export und Import benutzen). Ganze Zahlen sind
JSON-Zahlen ohne Nachkommastelle (`true` und `30.0` gelten nicht):

| Feld | Gültig |
|---|---|
| `leise_zeiten.zeitzone` | Text, den die Zeitzonendatenbank kennt; fehlt das Feld, gilt `Europe/Berlin` |
| `leise_zeiten.fenster` | Liste mit höchstens **32** Einträgen (leer ist erlaubt) |
| `fenster[].id` | Text, 1–32 Zeichen `[a-z0-9_-]`, eindeutig in der Liste |
| `fenster[].tage` | nicht leere Liste ohne Doppelte, ganze Zahlen 1 (Montag) bis 7 (Sonntag) |
| `fenster[].von`, `bis` | Text `HH:MM`, 24 Stunden; `bis` darf nicht gleich `von` sein; `bis` kleiner als `von` heißt: über Mitternacht |
| `fenster[].wirkung` | `leiser` oder `stumm` |
| `fenster[].grenze` | bei `leiser` Pflicht, ganze Zahl 0 bis 100; bei `stumm` entfällt sie (eine mitgesendete wird verworfen) |
| `gute_nacht.timer_min` | ganze Zahl 1 bis 240 |
| `gute_nacht.ausblenden_s` | ganze Zahl 5 bis 600 |
| `lesezeichen_tage` | ganze Zahl 0 bis 365 |

Unbekannte Felder **innerhalb** der Objekte werden wie auf der Box ignoriert und nicht gespeichert. Ist irgendein
Teil ungültig, wird die **ganze Änderung abgelehnt** (auch die gültigen Teile des Befehls): Fehlercode
`einstellung_ungueltig`; die `message` nennt die Stelle (`Diese Einstellung ist ungültig: fenster[0].von. Es wurde
nichts geändert.`; Pfade wie `fenster[2].grenze`, `leise_zeiten.zeitzone`, `gute_nacht.timer_min`,
`lesezeichen_tage`). Die Typen der drei Felder prüft nicht das WebSocket-Schema, sondern diese Prüfung, damit auch ein
Wert vom falschen Typ (`"14"`, `true`) den Pfad bekommt. **Hinweis:** HA prüft den Zeitzonen-Namen mit der eigenen,
die Box mit ihrer Zeitzonendatenbank; ein Name, den nur HA kennt, machte die Liste auf der Box ungültig
(`schema_ungueltig`, `mqtt-v1.md`).

Ausgabe: `{"geaendert", "konfig", "veroeffentlicht", "leise_zeiten", "gute_nacht", "lesezeichen_tage"}` (und
`hinweis_pegel`, wenn gesetzt): `geaendert`, `konfig` und `veroeffentlicht` wie bei `zuordnung/set` (Nr. 16), die
übrigen Felder sind der Stand **nach** dem Befehl (wie bei Nr. 35). Dieselben Werte wie schon gespeichert
ergeben `geaendert=false`, keine neue Revision und keine MQTT-Nachricht (Idempotenz). Fehler:
`einstellung_ungueltig`, `konfig_zu_gross`, `konfig_nicht_bereit`, `stand_veraltet` (12.11.). Recht: alltag (`leise_zeiten.zeitzone` wird ignoriert, `lesezeichen_tage` nur für Administratoren, 2.4). MQTT: veröffentlicht
`tobibox/config` (retained, Revision + 1, `erzeugt_am` jetzt), danach Export und Ereignis `konfig`/`geaendert`
(Abschnitt 1). Zuordnungen, `ton_pegel` und `hinweis_pegel` bleiben unverändert. Fähigkeit `einstellungen`.

Die **HA-Aktionen** `leise_zeiten_setzen`, `gute_nacht_setzen` und `lesezeichen_tage_setzen` (`services.yaml`)
rufen dieselbe Funktion (Abschnitt 1, W-10). Sie setzen Teile: Was in `leise_zeiten_setzen` (`zeitzone`, `fenster`)
oder `gute_nacht_setzen` (`timer_min`, `ausblenden_s`) fehlt, bleibt wie es ist; die Prüfung gilt für das fertige
Objekt. Zahlen wie `30.0` aus Reglern oder Vorlagen werden zu `30`.

### 3.12 Befehle ab 12.11. (HA-Oberfläche, Stufe A)

Alle Befehle dieses Abschnitts sind **neu** (Version 1 bleibt, Abschnitt 9). Rechte: 2.1; Schutz und Mengen: 2.4; Regeln im Einzelnen: Abschnitt 14. Jeder Befehl steht nur im Backend, wenn `hello.faehigkeiten` die genannte Fähigkeit zusagt (Regel in 14.1); Nr. 46 hat keine eigene Fähigkeit (ein älteres Backend antwortet `unknown_command`, die Seite zeigt dann „Die Seite ist veraltet“).

#### 37. `tobibox/folgen/list` (Fähigkeit `bibliothek`)

Sucht und blättert über **Folgen und Einzeltitel** aller Einträge (Suchansicht, Tobie für eine Folge).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `art` | `hoerspiel`, `hoerbuch`, `musik`, `geschichte` | nein | nur Folgen von Einträgen dieser Art |
| `text` | string, 2–100 Zeichen | nein | Suche (normalisiert, ohne Groß-/Kleinschreibung) im Titel der Folge |
| `filter` | array aus `ohne_tobie`, `neu`, `pruefen` | nein | wie bei `serien/list` (14.2) |
| `sortierung` | `titel` (Vorgabe), `neu` | nein | |
| `limit` | int 1–100 | nein | Vorgabe 60 |
| `offset` | int ≥ 0 | nein | Vorgabe 0 |

Ausgabe: `folgen` (array) und `gesamt`, `weitere`. Je Zeile: `serie_id`, `serie_name`, `serie_einzeln` (bool), `art`, `folge` (Name), `anzeige`, `nummer`, `kapitel` (int, Anzahl, 0 wenn keine Liste), `groesse_mb`, `tobies` (array von Tobie-Kurzform, direkt auf die Folge), `serie_hat_tobie` (bool), **(13.11., K8)** `cover_stand` (string oder `null`, wie in der Serie-Kurzform) und `dauer_s` (number oder `null`; bis Stufe A-2 immer `null`). Fehler: `medien_nicht_erreichbar` (nur wenn noch nie geprüft). Recht: lesen. Idempotent: ja. MQTT: –.

#### 38. `tobibox/serie/art_setzen` (Fähigkeit `bibliothek`)

Setzt die Art eines Eintrags von Hand.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `art` | `hoerspiel`, `hoerbuch`, `musik`, `geschichte` | **ja** | |

Setzt `art` und `art_quelle="manuell"` in `serie.json` und löscht in `pruefen_gruende` den Grund `art_geraten`. Ausgabe: `{"serie": <Serie-Kurzform>}`. Fehler: `serie_nicht_gefunden`, `medien_schreibfehler`. Recht: alltag. Idempotent: ja. MQTT: –.

#### 39. `tobibox/audio/bereit` (Fähigkeit `reinhoeren`)

Fragt **vor jedem Start** im Browser, ob eine Folge abspielbar ist, und liefert den signierten Pfad (14.5). Die Seite liest den Zustand nie aus dem Fehler des `<audio>`-Elements.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name der Folge |
| `track` | int ≥ 0 | nein | nur bei Ordner-Folgen (0-basiert) |
| `vorbereiten` | bool | nein | Vorgabe `true`: darf die Hörkopie anstoßen (14.8). Mit `false` nur den Zustand lesen. |

Ausgabe: `zustand` = `bereit`, `wird_vorbereitet` oder `fehlt`. Bei `bereit`: `pfad` (signierter Pfad `/api/tobibox/audio/…?authSig=…`, **24 Stunden** gültig, `AUDIO_LINK_GUELTIG_S`) und `quelle` (`original` oder `kopie`). Bei `wird_vorbereitet`: `warte_s` (Schätzung, int) und `position` (Platz in der Schlange, int ≥ 1). Bei `fehlt`: `grund` = `zu_lang`, `zeitgrenze`, `unplausibel`, `kodieren_fehlgeschlagen`, `kein_speicher`, `medien_nicht_erreichbar` oder `ffmpeg_fehlt`. Fehler: `folge_nicht_gefunden`, `serie_nicht_gefunden`, `hoerkopie_warteschlange_voll`, `zu_viele_aenderungen`. Recht: alltag. Idempotent: ja (Anstoßen einer schon wartenden Kopie ändert nichts). MQTT: –.

#### 40. `tobibox/hoerstelle/get` (Fähigkeit `reinhoeren`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |

Ausgabe: `weiter` (object `{folge, position_s, track, anteil, rest_s, zeit}` oder `null`) und `folgen` (object: Name der Folge → `{position_s, dauer_s, fertig, zeit}`), jeweils nur die **eigene** Hörstelle des Anfragenden. Fehler: `serie_nicht_gefunden`. Recht: lesen. Idempotent: ja. MQTT: –.

#### 41. `tobibox/hoerstelle/set` (Fähigkeit `reinhoeren`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | **ja** | |
| `folge` | string | **ja** | Name der Folge |
| `position_s` | Zahl ≥ 0 | **ja** | Stelle in Sekunden (im Track, bei Ordner-Folgen) |
| `dauer_s` | Zahl > 0 | **ja** | Länge laut Browser |
| `track` | int ≥ 0 | nein | bei Ordner-Folgen |
| `fertig` | bool | nein | |

Prüfung: Serie und Folge gibt es; `0 ≤ position_s ≤ dauer_s + 2`. **Ist `dauer_s` der Folge im Store `tobibox.medieninfo` bekannt, nimmt das Backend diesen Wert und ignoriert den gesendeten** (der Aufrufer bestimmt die Prüfung nie selbst); nur bei unbekannter Dauer gilt der gesendete Wert bis höchstens `HOERSTELLE_DAUER_UNBEKANNT_MAX_S`. `fertig` wird auch gesetzt, wenn `position_s ≥ dauer_s − 2`. Antwortet **sofort** (`{}`), geschrieben wird gesammelt (14.6). Fehler: `serie_nicht_gefunden`, `folge_nicht_gefunden`, `invalid_format` (Werte außerhalb), `zu_viele_aenderungen`. Recht: alltag (nur die eigene Hörstelle). Idempotent: ja. MQTT: –.

#### 42. `tobibox/hoerstelle/liste` (Fähigkeit `reinhoeren`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `limit` | int 1–12 | nein | Vorgabe 8 |

Ausgabe: `eintraege` (array): angefangene, nicht fertige Einträge des Anfragenden, zuletzt angehört zuerst; je Eintrag `serie_id`, `name`, `folge`, `position_s`, `anteil`, `rest_s`, `zeit` (Reihe „Am Handy weiterhören“). Recht: lesen (nur die eigene). Idempotent: ja. MQTT: –.

#### 43. `tobibox/einsortierung/neu` (Fähigkeit `einsortier_wunsch`)

„Anders einsortieren“: Holt die Folgen, die ein Eingangs-Eintrag erzeugt hat, aus den Medien in den Eingang zurück und sortiert sie mit einem neuen Wunsch (14.4) neu ein.

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | `id` aus `eingang/list` |
| `ziel` | `neu`, `ergaenzen`, `einzeln` | **ja** | wie beim Upload (14.4) |
| `art` | `hoerspiel`, `hoerbuch`, `musik`, `geschichte` | je nach `ziel` | |
| `name` | string, 1–100 Zeichen | je nach `ziel` | |
| `serie_id` | string | bei `ergaenzen` | |

Nur möglich, solange die Bedingungen aus 2.4 erfüllt sind (`pruefen=true` oder höchstens 24 Stunden alt; nichts geändert). Die Serien, die der Eintrag neu angelegt hatte, verschwinden mit ihm in den Papierkorb (`grund="manuell"`, `geloescht_von` gesetzt). Ausgabe: `{"gestartet": true}`; das Ergebnis kommt als Ereignis `eingang` (`neu_einsortiert`). Fehler: `eintrag_nicht_gefunden`, `neu_einsortieren_nicht_moeglich`, `wunsch_ungueltig`, `serie_nicht_gefunden`, `sortierung_laeuft`, `zu_viele_aenderungen`, `medien_schreibfehler`. Recht: alltag. Idempotent: nein (der zweite Aufruf liefert `eintrag_nicht_gefunden` oder `neu_einsortieren_nicht_moeglich`). MQTT: –. **Machbarkeit offen:** Vertrag W kennt heute keinen Weg Medien → Eingang. Zeigt Paket A3e, dass er zu teuer ist, entfällt dieser Befehl samt Fähigkeitsteil (Entscheidung Tobias, Frage 25: Rückfall „Papierkorb und neu hochladen“).

#### 44. `tobibox/cover/neu_suchen` (Fähigkeit `cover`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | nein | fehlt: alle Einträge |

Löscht `cover.jpg` und die Marke `cover_suche` und startet die Suche im Hintergrund neu (14.3). Berührt nie `cover-eigen.jpg`. Ausgabe: `{"gestartet": <bool>, "eintraege": <int>}`. Fehler: `serie_nicht_gefunden`, `medien_nicht_erreichbar`. Recht: admin. Idempotent: ja. MQTT: –.

#### 45. `tobibox/hoerkopie/neu_erzeugen` (Fähigkeit `hoerkopie`)

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `serie_id` | string | nein | fehlt: alle Folgen mit Zustand `fehler` |

Löscht Kopie und Marke und stellt die Folge neu in die Warteschlange (14.8). Ausgabe: `{"eingereiht": <int>}`. Fehler: `serie_nicht_gefunden`, `hoerkopie_warteschlange_voll`, `medien_nicht_erreichbar`. Recht: admin. Idempotent: ja. MQTT: –.

#### 46. `tobibox/papierkorb/restore_letzte_stunde`

Holt alles zurück, was in der **letzten Stunde** in den Papierkorb kam (Sicherung gegen Fehlbedienung, 2.4). Eingabe: `bestaetigt` (bool, muss `true` sein, sonst `invalid_format`). Ausgabe: `{"wiederhergestellt": <int>, "uebersprungen": [{"eintrag_id", "code"}…]}`; Einträge, die sich nicht zurückholen lassen (zum Beispiel `datei_existiert`, `serie_existiert`), stehen mit ihrem Code in `uebersprungen`, der Rest wird trotzdem zurückgeholt. Fehler: `medien_nicht_erreichbar`, `medien_schreibfehler`. Recht: admin. Idempotent: Endzustand ja. MQTT: –. Ereignisse `medien`/`papierkorb_geaendert` und `serien_geaendert`.

### 3.13 Warteschlange „Nächster neuer Tobie“ (ab 13.11., Fähigkeit `warteschlange`)

**Prinzip (X13).** Tobies und Karten werden nicht beschrieben; die Box liest nur die Kennung. Statt eines Countdowns legt man **vorab am Handy** fest, was der **nächste unbekannte Tobie** spielen soll („Vormerkung“). Legt jemand danach einen unbekannten Tobie auf, ordnet **nur Home Assistant** ihn zu. Box und MQTT bleiben unverändert: HA nutzt die vorhandene Meldung `tobibox/<box>/unknown/<uid>` mit `art="unbekannt"` (`mqtt-v1.md`, 3.5) und die vorhandenen `ack`-Gründe (3.6). Die Warteschlange liegt im HA-Speicher (derselbe `Store` wie „Neue Tobies“, eigener Schlüssel `warteschlange`), getrennt von der Konfiguration: keine Revision, nicht auf MQTT, nicht im Export, nicht auf dem NAS, Teil der HA-Sicherung. Im Alltag ersetzt sie den Lernmodus (3.6, nur noch admin). Eine HA-Aktion für Automationen gehört **nicht** zu dieser Änderung.

**Eintrag „Vormerkung“** (Ausgabe von `warteschlange/set` und `warteschlange/list`, Ereignis `angelegt`):

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | string, 12 Zeichen `[0-9a-f]` | vom Backend vergeben, bleibt gleich |
| `box` | string oder `null` | Box-Name; `null` = **irgendeine Box** *(Lücke: die Skizze im Design nannte `alle`; ein Box-Name `alle` wäre zulässig und würde kollidieren)* |
| `ziel` | object | Ziel (Gemeinsame Objekte): `serie`, `folge` oder `aktion` (`status`, `gute_nacht`); nie die Überraschungs-Serie. `playlist` kommt additiv mit Stufe C |
| `serie_name` | string oder `null` | wie bei `zuordnung/list`; `null`, wenn die Serie fehlt |
| `folge_anzeige` | string oder `null` | nur bei `typ="folge"` |
| `folge_vorhanden` | bool oder `null` | nur bei `typ="folge"` |
| `angelegt_von` | object oder `null` | `{"id", "name"}` des HA-Benutzers (wie `geloescht_von`, 3.3); `null` ohne Benutzer |
| `angelegt_am` | string | Zeitstempel |
| `name` | string oder `null` | **(13.11., K7)** Name, den der Tobie bekommt, wenn er die Vormerkung nimmt; `null` ohne Namen (auch bei Einträgen, die vor K7 angelegt wurden) |
| `position` | int ≥ 1 | Platz in der Reihenfolge der Anlage über alle Boxen („Nr. 1 von 2“); 1 wird als Erster bedient |

Das Backend merkt sich zusätzlich eine laufende Nummer: Die Reihenfolge der Anlage entscheidet, nicht der Zeitstempel (er hat nur Sekunden).

**Regeln.** *(Lücke)* kennzeichnet, was das Design offen ließ und hier festgelegt ist.

1.  **Nur unbekannte Tobies, nie umhängen.** Abgeglichen wird nur eine Meldung mit `art="unbekannt"` (nie `gelernt`) und nur, wenn die Kennung in den Zuordnungen **nicht** steht. Das Backend schreibt die Zuordnung mit der Regel „es gibt noch kein Ziel“ (wie `erwartet_ziel: null` bei `zuordnung/set`) unter der Sperre der Konfiguration. Hat die Kennung inzwischen ein Ziel (zweite Box, anderes Fenster), geschieht nichts: der Eintrag bleibt, die Box bekommt `bekannt`. Ein bekannter Tobie spielt weiter wie bisher und wird nur bewusst über `zuordnung/set` mit `erwartet_ziel` umgestellt.
2.  **Welcher Eintrag.** Passend sind Einträge mit `box` = der meldenden Box und Einträge mit `box=null`. Die Meldung nimmt den **ältesten** (FIFO). Eine Vormerkung für eine Box und eine für „irgendeine Box“ **konkurrieren nach Anlagezeit**; der Ältere gewinnt, auch wenn der Jüngere genauer passt. Beispiel: A „irgendeine Box“ (10:00), B „Box 1“ (10:05). Der erste Tobie auf Box 1 nimmt A, der nächste auf Box 1 nimmt B. Der erste Tobie auf Box 2 nimmt A; danach wartet für Box 2 nichts mehr (B bleibt für Box 1). Gibt es keinen passenden Eintrag mehr, gilt der normale Weg A (6.1). *(Lücke: das Beispiel und die Folge für Box 2 sind aus Design 5.13, Punkt „Zwei Einträge“, abgeleitet.)*
3.  **Zwei Einträge für dieselbe Box** sind erlaubt und werden der Reihe nach bedient. Abgelehnt wird nur derselbe Eintrag: gleiche `box` **und** gleiches `ziel` (`warteschlange_doppelt`). „Irgendeine Box“ und „Box 1“ mit gleichem Ziel sind verschieden. *(Lücke: was „derselbe“ heißt.)*
4.  **Höchstens `WARTESCHLANGE_MAX` (5) Einträge** zugleich, über alle Boxen (`warteschlange_voll`). Prüfreihenfolge in `warteschlange/set`: Eingabe, Ziel und Name (`name_ungueltig`, K7), dann `warteschlange_doppelt`, dann `warteschlange_voll`. *(Lücke: ein doppelter Eintrag bei voller Warteschlange meldet „doppelt“.)*
5.  **Kein Höchstalter** (Design: „Kein Zeitlimit“). Ein Eintrag bleibt, bis ein Tobie ihn nimmt, jemand ihn abbricht oder sein Ziel oder seine Box fehlt (Regel 10). Es gibt dafür bewusst keine Konstante. `angelegt_am` und `angelegt_von` stehen in der Liste, damit man Vergessenes findet.
6.  **Was als „danach“ zählt.** Jede Meldung `unbekannt`, die HA verarbeitet, solange der Eintrag besteht. Es gibt keinen Vergleich von Zeitstempeln (die Uhr der Box kann abweichen, `zeit_ok`). Auch eine Kennung, die schon in „Neue Tobies“ steht und erneut aufgelegt wird, ist weiter unbekannt und kann einen Eintrag nehmen. *(Lücke. Folge: Ein liegengebliebener, nie zugeordneter Tobie kann einen Eintrag nehmen, wenn er vor dem gewünschten wieder aufgelegt wird. „Rückgängig“, 3.5, und die Seite des Tobies stellen es um.)*
7.  **Ablauf bei einem Treffer.** Unter einer Sperre für die Warteschlange (Reihenfolge der Sperren: Abschnitt 1), damit zwei gleichzeitige Meldungen nie denselben Eintrag nehmen:
    *   **a.** Das Ziel wird wie bei `zuordnung/set` geprüft. Fehlt es (Serie im Papierkorb oder gelöscht, Folge weg): Der Eintrag wird verworfen (Ereignis `abgebrochen`, `grund="ziel_fehlt"`) und der **nächste passende** Eintrag geprüft. Gibt es keinen, gilt der normale Weg A mit der Karte „Neuer Tobie“. *(Lücke: Das Design verwirft den Eintrag und zeigt die Karte; mit zwei Einträgen bliebe der zweite sonst ungenutzt.)*
    *   **b.** Das Backend schreibt die Zuordnung (Revision + 1, `tobibox/config`) wie `zuordnung/set` ohne `ueberschreiben`, als System (kein Benutzer, keine Mengen, 2.4). **K7 (13.11.):** Hat die Vormerkung einen `name`, wird er der Name des Tobies (wie `name` bei `zuordnung/set`); sonst bleibt die Zuordnung ohne Namen. Die Kennung hatte kein Ziel (Regel 1), also ist `vorher` (3.5, K6) `null`. **Zuordnung und Austragen des Eintrags gehen in einem Schreibvorgang des Speichers:** Nach einem Absturz gilt beides oder nichts. *(Lücke: sonst könnte ein Eintrag zweimal verbraucht werden.)*
    *   **c.** Die Kennung wird **nicht** in „Neue Tobies“ aufgenommen (kein `neu`, auch kein Flackern der Karte). Stand sie schon dort, wird sie entfernt (`neue_tobies` `entfernt`, `grund="zugeordnet"`).
    *   **d.** `ack` an die meldende Box mit `grund="bekannt"` (die Kennung steht jetzt in den Zuordnungen, W-11; `mqtt-v1.md`, 3.6 kennt den Grund), **nachdem** die Konfiguration gespeichert und veröffentlicht ist. Ohne PUBACK (Broker weg) wird trotzdem bestätigt; die Veröffentlichung holt das Backend wie immer nach. Liegt der Tobie noch auf, wechselt die Box mit der neuen Liste auf das Ziel (`mqtt-v1.md`, 4.1, Schritt 6); bis dahin spielt sie kurz die Überraschungs-Serie. *(Lücke: Das Design nennt den `ack` nicht.)*
    *   **e.** Ereignis `warteschlange` `abgearbeitet` (4.8). Es ist der **einzige** Hinweis für die Meldung „Box 1: Der neue Tobie spielt jetzt …“ mit „Name geben“; ein Feld `automatisch_zugeordnet` braucht es nicht. *(Abweichung von der Skizze im Design, die `automatisch_zugeordnet` und `ziel` an `neue_tobies/list` nennt: Ein zugeordneter Tobie steht nie in dieser Liste, darum sind `uid` und `ziel` im Ereignis.)*
    *   **f.** Scheitert **b** (`konfig_nicht_bereit`, `konfig_zu_gross`, Speicherfehler): Nichts ist geändert, der Eintrag bleibt, die Meldung läuft den normalen Weg A. Das Backend schreibt eine Protokollzeile (Warnung); ein Ereignis gibt es nicht. *(Lücke.)*
8.  **Doppelte Meldung** derselben Kennung (Prellen, beide Boxen, erneute Zustellung nach einem Absturz): Die zweite Meldung findet die Kennung in den Zuordnungen (Regel 1) und bekommt `bekannt`. Es entsteht **eine** Zuordnung, **ein** Eintrag wird verbraucht.
9.  **Zusammenspiel mit dem Lernmodus eines Administrators.** Der Lernmodus hat Vorrang und stört die Warteschlange nicht. Eine Box im Lernmodus meldet aufgelegte Tobies als `gelernt` und spielt nichts (`mqtt-v1.md`, 4.2): Die Warteschlange berührt das nie; die Vormerkungen bleiben stehen. Kommt für eine Box, für die ein **lebender** Lernmodus-Vorgang läuft (3.6), trotzdem eine Meldung `unbekannt` (zum Beispiel eine, die schon vor dem Start unterwegs war), nimmt die Warteschlange sie **nicht**; es gilt der normale Weg A. Endet der Lernmodus ohne Zuordnung (`abgelaufen`, `abgebrochen`, `abgelehnt` mit unbekannter Kennung) und meldet die Box den Tobie danach erneut als `unbekannt`, ist das wieder eine ganz normale Meldung (Regeln 1 und 2). `lernmodus/start` wird durch Vormerkungen nicht verhindert. *(Lücke.)*
10. **Ziel oder Box ist weg.** Ein Ziel, das inzwischen fehlt, bemerkt das Backend **beim Auflegen** (Regel 7a); in der Liste zeigt `serie_name=null` bzw. `folge_vorhanden=false`, dass es fehlt. Wird die Serie später aus dem Papierkorb zurückgeholt, bevor ein Tobie aufliegt, gilt der Eintrag weiter. Ein Eintrag mit einer Box, die in der Einrichtung der Integration nicht mehr vorkommt, wird beim Start der Integration verworfen (Ereignis `abgebrochen`, `grund="box_unbekannt"`). *(Lücke.)*
11. **Neustart von HA.** Die Einträge bleiben: Das Backend speichert sofort bei jedem Anlegen, Abbrechen und Abarbeiten (kein verzögertes Speichern, anders als bei „Neue Tobies“). Offene Ereignisse gehen verloren; die Seite holt den Stand mit `warteschlange/list` (Abschnitt 4: Ereignisse sind nur Hinweise). Es läuft kein Zeitgeber.
12. **Rückgängig (X20d).** Nach einem Treffer kann die Seite mit `zuordnung/remove` und `erwartet_ziel` (und `als_neu`) zurücknehmen (3.5). Die Meldung des Designs zeigt nach einem Treffer „Name geben“, nicht „Rückgängig“; beides geht.
13. **Protokoll und Mitteilung.** Jede Anlage, jedes Abbrechen und jeder Treffer schreibt eine Protokollzeile (Stufe Information): Benutzer, Zeit, Box, Ziel, beim Treffer die Kennung und die meldende Box. Eine **Mitteilung** (`persistent_notification`) an Administratoren gibt es **nicht**: Ein Treffer fügt etwas hinzu und lässt sich mit „Rückgängig“ zurücknehmen; anders als beim Löschen (2.4) geht nichts verloren. *(Lücke.)*
14. **Rechte und Mengen.** Alle drei Befehle sind `alltag`. Jeder Benutzer darf auch Einträge anderer abbrechen (ein Haushalt, ein Gerät, das Handy der Partnerin). Für Nicht-Administratoren gilt `WARTESCHLANGE_AENDERUNGEN_JE_MINUTE` für `warteschlange/set` und `warteschlange/abbrechen` zusammen (`zu_viele_aenderungen`); Administratoren sind ausgenommen (2.4).

#### 47. `tobibox/warteschlange/set` (Fähigkeit `warteschlange`)

Legt eine Vormerkung an: „Der nächste neue Tobie auf <Box> oder irgendeiner Box spielt <Ziel>.“

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `box` | string oder `null` | **ja** | Box-Name oder `null` für „irgendeine Box“. Die Box muss eingerichtet sein, aber **nicht** online: Die Warteschlange liegt in HA, auch eine ausgeschaltete Box geht. |
| `ziel` | object | **ja** | `typ` `serie`, `folge` oder `aktion` (`status`, `gute_nacht`), geprüft wie bei `zuordnung/set` (3.5); die Überraschungs-Serie ist verboten (`ziel_ungueltig`) |
| `name` | string, 1–60 Zeichen, oder `null` | nein | **(13.11., K7)** Name für den Tobie, der die Vormerkung nimmt; gleiche Regeln wie bei `zuordnung/set` (3.5): Steuerzeichen entfernt, Leerraum gekürzt, danach leer oder zu lang: `name_ungueltig`. Fehlt das Feld oder ist es `null`, bekommt die Vormerkung keinen Namen. Der Name gehört **nicht** zu „derselbe Eintrag“ (Regel 3). |
| `anfrage_id` | string | nein | siehe 2.2 |

Ist `konfig.zustand` nicht `ok`, lehnt das Backend sofort ab (`konfig_nicht_bereit`): Ein Treffer könnte nichts zuordnen. *(Lücke.)*

Ausgabe: `{"eintrag": <Vormerkung>, "gesamt": <int>}`. Fehler: `box_unbekannt`, `ziel_ungueltig`, `serie_nicht_gefunden`, `folge_nicht_gefunden`, `name_ungueltig` (13.11., K7), `konfig_nicht_bereit`, `warteschlange_doppelt`, `warteschlange_voll`, `zu_viele_aenderungen`, `anfrage_id_konflikt`. Die vorhandenen Codes reichen für alles außer „doppelt“ und „voll“. Recht: alltag. Idempotent: mit `anfrage_id` (gleiche `anfrage_id` und gleiche Felder liefern dieselbe Antwort, ohne einen zweiten Eintrag); ohne `anfrage_id` antwortet ein zweites Senden mit `warteschlange_doppelt`. MQTT: –. Ereignis `warteschlange` `angelegt`.

#### 48. `tobibox/warteschlange/list` (Fähigkeit `warteschlange`)

Keine Eingabe. Ausgabe: `{"eintraege": [<Vormerkung>…], "gesamt": <int>}`, nach `position` aufsteigend (höchstens `WARTESCHLANGE_MAX` Einträge, kein Blättern nötig). Liest aus dem Speicher und aus dem Zwischenspeicher der Serien, nie frisch von der Freigabe (W-28). Fehler: keine außer den allgemeinen. Recht: alltag. Idempotent: ja. MQTT: –.

#### 49. `tobibox/warteschlange/abbrechen` (Fähigkeit `warteschlange`)

Nimmt eine Vormerkung zurück („Nicht mehr warten“).

| Eingabe | Typ | Pflicht | Bedeutung |
|---|---|---|---|
| `eintrag_id` | string | **ja** | `id` der Vormerkung. **Nicht `id`:** das Feld `id` einer WebSocket-Nachricht ist die Nachrichtennummer der Verbindung und kann keine Eingabe sein (Abweichung vom Entwurf, gefunden beim Bau von A9c, 13.11.) |

Ausgabe: `{"abgebrochen": <bool>}` (`false`: gab es nicht mehr, weil schon abgearbeitet oder abgebrochen; **kein Fehler**, wie bei `neue_tobies/verwerfen`). Fehler: `zu_viele_aenderungen`. Recht: alltag. Idempotent: ja. MQTT: –. Ereignis `warteschlange` `abgebrochen` (`grund="nutzer"`). Die Positionen der übrigen Einträge rücken nach.

## 4. Ereignisse (Abo `tobibox/subscribe`)

Alle Ereignisse haben dieselbe Hülle (Inhalt des Feldes `event` der HA-Nachricht):

```json
{ "v": 1, "thema": "boxen", "art": "geaendert", "daten": { … } }
```

*   `thema` ist eines der abonnierten Themen, `art` die Art des Ereignisses, `daten`
    der Inhalt. Neue `art`-Werte und neue Felder können ohne Versionsänderung
    kommen (Abschnitt 9); die Seite ignoriert, was sie nicht kennt.
*   **`art="snapshot"`**: kommt einmal je Thema direkt nach dem Abonnieren (auch nach
    einem erneuten Abonnieren durch den Verbindungsaufbau der Seite). Er trägt nur
    den kleinen Zustand, den das Thema braucht, **nie** ganze Listen: Listen holt die
    Seite mit den Befehlen. So bleibt jede Nachricht klein (Abschnitt 8).
*   **Nur Hinweise, keine Quelle der Wahrheit.** Verpasst die Seite ein Ereignis
    (Verbindung weg), stimmt der Zustand nach dem nächsten Snapshot und einem
    `list`/`get` wieder. HA baut die Verbindung der Oberfläche selbst neu auf und
    abonniert dabei erneut.
*   **Bündeln (W-23):** Das Backend fasst nur die Ereignisse `geaendert` (Themen
    `boxen`, `konfig`, `eingang`) und `serien_geaendert` zusammen: höchstens **eines je
    Thema und Box (bzw. Serie) und Sekunde**. Ereignisse mit eigenem Inhalt
    (`boxen`/`ereignis`, `lernmodus`-Zustände, `neu_einsortiert`, `abweichung`,
    `fortschritt`) werden **nie** zusammengefasst oder verschluckt. Die HA-Warteschlange
    je Verbindung ist begrenzt (4096 Nachrichten, Abschnitt 8); Ereignisse sind darum
    selten und klein.

### 4.1 Thema `boxen`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"boxen": [{"box", "online", "konfig_stand"}…]}` |
| `geaendert` | ein vollständiges Box-Objekt (3.7, ohne `ereignisse`), wenn sich `online`, `status` oder `konfig_stand` änderte (auch auf oder von `voraus`) |
| `ereignis` | `{"box": <string>, "ereignis": {"id", "ts", "art", "daten", "text"}}` für jede neue Meldung von `…/event` (z. B. `liste_abgelehnt`) |

### 4.2 Thema `neue_tobies`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"gesamt": <int>}` |
| `neu` | `{"eintrag": <Eintrag>}`, eine Kennung erscheint zum ersten Mal |
| `aktualisiert` | `{"eintrag": <Eintrag>}`, neue Meldung zu einer bekannten Kennung |
| `entfernt` | `{"uid": <string>, "grund": "zugeordnet" \| "verworfen"}` |

**Seit 13.11.:** Trifft eine Meldung eine Vormerkung (3.13), gibt es **kein** `neu` für diese Kennung. Stand sie schon in der Liste, kommt `entfernt` mit `grund="zugeordnet"`; die Meldung für die Seite steht im Thema `warteschlange` (4.8).

### 4.3 Thema `lernmodus`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"vorgaenge": […]}` (siehe unten) |
| `zustand` | **(09.11., Befund AP 3.1)** ein Vorgang hat den Zustand gewechselt oder sich geändert; `daten` wie in der Tabelle unten |

Gilt je Box und Vorgang. `daten` von `zustand`:

| Feld | Typ | Bedeutung |
|---|---|---|
| `box` | string | |
| `befehl_id` | string | |
| `zustand` | string | siehe unten |
| `ziel` | object | Ziel des Vorgangs |
| `beginn`, `frist_bis` | string | wie bei `lernmodus/start` |
| `rueckfrage_bis` | string oder `null` | bei `rueckfrage`: bis wann `lernmodus/antwort` gilt (6.2, Schritt 3) |
| `uid` | string oder `null` | gemeldete Kennung (ab `rueckfrage`/`zugeordnet`) |
| `bisher` | object oder `null` | bei `rueckfrage`: das bisherige Ziel der Kennung |
| `grund` | string oder `null` | bei `abgelehnt`, `box_lehnt_ab`, `abgelaufen`: Ursache; bei `zugeordnet` `unveraendert`, wenn der Tobie das Ziel schon hatte |
| `text` | string oder `null` | Klartext |

`zustand`: `wartet` (Befehl gesendet, noch kein Tobie gemeldet), `rueckfrage` (Kennung
ist schon zugeordnet; die Seite zeigt die Frage und antwortet mit `lernmodus/antwort`),
`zugeordnet` (Ende), `abgelehnt` (Ende; `grund` ∈ `nutzer`, `abgelaufen`,
`konfig_zu_gross`, `speicherfehler`, `ziel_fehlt`, `konfig_nicht_bereit`),
`abgebrochen` (Ende), `abgelaufen` (Ende; `grund` ∈ `frist` = `frist_bis` ohne Meldung,
`box_beendet` = die Box meldet den Lernmodus als beendet, `kein_status` = 30 s ohne
Lernmodus-Status; W-05), `box_lehnt_ab` (Ende; `grund` ∈ `bedingung`, `zeit_unsicher`).

`snapshot`: `{"vorgaenge": [<daten ohne Ende-Zustände>…]}` (höchstens ein Vorgang je
Box).

### 4.4 Thema `medien`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"pruefung_laeuft": <bool>, "geprueft_am": <string oder null>}` |
| `serien_geaendert` | `{"serie_ids": [<string>…]}` (Prüfung, anderer Nutzer, Upload, Einsortieren, Korrektur oder Papierkorb haben etwas geändert; die Seite lädt `serien/list` bzw. `serie/get` neu) |
| `pruefung_fertig` | `{"geprueft_am": <string>, "neue_serien": <int>, "neue_folgen": <int>, "entfernte_folgen": <int>, "hinweise": <int>}` |
| `papierkorb_geaendert` | `{}` |

### 4.5 Thema `eingang`

| `art` | `daten` |
|---|---|
| `snapshot` | `{"offen": <int>, "blockiert": <int>, "sortierung_laeuft": <bool>, "geprueft_am": <string oder null>}` |
| `geaendert` | `{}`: die Liste im Eingang hat sich geändert; die Seite lädt `eingang/list` neu |
| `neu_einsortiert` | `{"eintrag_id", "eintrag_name", "ergebnis": [<wie in Eingangs-Eintrag>…], "hinweise": [<wie dort>…], "zaehler": {"folgen", "serien_neu", "pruefen", "doppelt", "blockiert"}}`: ein Eintrag wurde ganz oder teilweise einsortiert („neu einsortiert“). Eines je Eintrag, nie zusammengefasst. |
| `durchlauf_fertig` | `{"geprueft_am": <string>, "zaehler": {"eintraege", "folgen", "serien_neu", "pruefen", "doppelt", "blockiert"}}` |

Bleibt etwas `blockiert` (Kopierschutz, defekt), legt das Backend zusätzlich eine
HA-Benachrichtigung (`persistent_notification`) an, einmal je Eintrag.

### 4.6 Thema `konfig`

| `art` | `daten` |
|---|---|
| `snapshot`, `geaendert` | `{"konfig": <Konfig-Stand>}`. `geaendert` kommt nach jeder Änderung durch `zuordnung/*`, `lernmodus/antwort`, `folge/verschieben`, `serien/zusammenfuehren`, `liste/neu_ausrollen`, `konfig/aus_export`, `einstellungen/set` (auch von einem anderen Fenster oder einer Aktion aus) und bei jedem Wechsel von `zustand`, `export_ok`. Die Seite lädt dann `zuordnung/list` und, wenn `hello` die Fähigkeit `einstellungen` zusagt, `einstellungen/get`. |
| `abweichung` | `{"box", "grund": "voraus" \| "revision_zu_niedrig", "box_liste_id", "box_revision", "ha_revision"}` (W-02): eine Box hat einen neueren Stand als HA oder lehnt die Liste von HA wegen zu niedriger Revision ab. Die Seite zeigt „Die Box hat einen neueren Stand als HA. Bitte ‚Liste neu ausrollen‘ (oder aus dem Export holen).“ Die Integration erhöht die Revision **nie** von selbst auf den Stand der Box. |
| `export_fehler` | `{"seit": <string>, "text": <string>}`: der Export auf das NAS schlug fehl (der Befehl selbst gelang). |
| `export_ok` | `{"export_geschrieben_am": <string>}`: der Export ist nachgeholt. |

### 4.7 Thema `upload`

Das Backend sendet die Ereignisse eines Uploads an **alle Abos des Nutzers, der ihn
gestartet hat** (Thema `upload`); die Seite filtert nach `upload_id` (W-04). Die
`upload_id` kommt nur im HTTP-Körper an, das Backend kennt keine Verbindung zu einem
Upload. Der Fortschritt des Sendens ist Sache des Browsers (5.7); das Thema meldet die
Phase **nach** dem Empfang.

| `art` | `daten` |
|---|---|
| `snapshot` | `{}` |
| `fortschritt` | `{"upload_id", "zustand": "pruefe" \| "fertig" \| "fehler", "bytes": <int>, "code": <string oder null>}` – `pruefe` einmal (Prüfung nach 5.4), `fertig`/`fehler` einmal am Ende (dann liegt die HTTP-Antwort schon vor, oder der Client ist nicht mehr da, 5.2). **(09.11., AP 4.7, Erweiterung v1.1)** Bei `zustand="fertig"` kommen zwei Felder dazu: `datei` (Name der Datei **im Eingang**, nach der Namensregel von Abschnitt 12, also wie `eingang_name` der HTTP-Antwort; mit Suffix ` (2)`, wenn der Name schon vergeben war) und `pruefung` (`ok`, `warnung` oder `nicht_moeglich`, wie in der HTTP-Antwort, 5.5). Bei `pruefe` und `fehler` fehlen sie. So erfährt die Seite das Ergebnis auch dann, wenn ihre Verbindung vor der Antwort abbrach. Nur auswerten, wenn `hello.faehigkeiten` `upload_fertig_details` zusagt. |

### 4.8 Thema `warteschlange` (ab 13.11., Fähigkeit `warteschlange`)

Die Ereignisse sind Hinweise (Abschnitt 4); die Quelle der Wahrheit ist `warteschlange/list`. Sie gehen an alle Abos des Themas und werden **nie** gebündelt. Nach jedem Ereignis lädt die Seite die Liste neu, weil sich die `position` der übrigen Einträge ändert.

| `art` | `daten` |
|---|---|
| `snapshot` | `{"gesamt": <int>}` |
| `angelegt` | `{"eintrag": <Vormerkung>}` |
| `abgebrochen` | `{"id": <string>, "grund": "nutzer" \| "ziel_fehlt" \| "box_unbekannt"}`: `nutzer` = `warteschlange/abbrechen`; `ziel_fehlt` = beim Auflegen fehlte das Ziel (3.13, Regel 7a; danach kommt die Karte „Neuer Tobie“, wenn kein weiterer Eintrag passt); `box_unbekannt` = beim Start verworfen (Regel 10) |
| `abgearbeitet` | `{"id": <string>, "uid": <string>, "box": <string>, "ziel": <Ziel>, "serie_name": <string oder null>, "folge_anzeige": <string oder null>, "angelegt_von": <object oder null>, "name": <string oder null>}`: ein Tobie hat die Vormerkung genommen; `name` (13.11., K7) ist der Name, den der neue Tobie bekommen hat (`null`: keiner, dann zeigt die Seite „Name geben“); `box` ist die **meldende** Box, `uid` die Kennung des neuen Tobies (für „Name geben“). Das Ereignis kommt nach dem Speichern der Zuordnung (3.13, Regel 7). |

## 5. Hochladen (HTTP)

Ein Upload legt die Datei in den **Eingang** (Entscheidung M, Abschnitt 11). Er
durchläuft dieselbe Einsortierung wie alles, was Tobias vom PC in den Eingang legt.

### 5.1 Endpunkt

*   **Pfad:** `POST /api/tobibox/upload`. Eine Datei je Anfrage; mehrere Dateien sendet
    die Seite nacheinander.
*   **Umsetzung:** eine Klasse `TobiboxUploadView(HomeAssistantView)` mit `url`, `name =
    "api:tobibox:upload"`, `requires_auth = True` (Vorgabe), `cors_allowed = False`
    (Vorgabe); registriert mit `hass.http.register_view(...)` in `http.py`.
*   **Anmeldung:** Header `Authorization: Bearer <Zugriffstoken>` (das Token der
    HA-Sitzung; die Seite holt es aus dem `hass`-Objekt und erneuert es **vor** dem
    Start eines Uploads, falls es abgelaufen ist; das Token gilt nur beim Start der
    Anfrage, ein laufender Upload bricht nicht ab). Ohne gültiges Token antwortet HA mit
    401. Seit 12.11. gibt es keine Administrator-Prüfung mehr (2.1, W-19 entfällt): jeder angemeldete Nutzer darf hochladen; die Schutzgrenzen stehen in 2.4.
*   **Format des Körpers:** `multipart/form-data` (Design: `request.multipart()`).
    Felder **in dieser Reihenfolge**, alle außer `datei` optional: `upload_id` (Text,
    8–64 Zeichen `[0-9A-Za-z-]`, von der Seite erzeugt), `serie_id` (Text: die Serie,
    in deren Ansicht der Nutzer hochlädt; **Vorgabe** für die Einsortierung, 11.5),
    `gruppe` (Text, 8–64 Zeichen `[0-9A-Za-z-]`: Dateien mit gleicher `gruppe` kommen in
    einen gemeinsamen Eingangs-Ordner `Upload <erste 8 Zeichen>` und bilden zusammen
    ein Album, wenn die Tags es hergeben), dann `datei` (die Datei, mit `filename`).
    **(12.11., Fähigkeit `einsortier_wunsch`)** Zusätzlich, ebenfalls vor `datei`: `ziel`, `art`, `name`, `gruppe_anzahl` (14.4).
    Weitere Felder werden ignoriert, Felder nach `datei` nicht gelesen.
*   **Der Körper wird nie ganz gelesen.** Das Backend liest nur im Strom
    (`request.multipart()`, `part.read_chunk(...)`), keinesfalls `request.read()`,
    `request.post()` oder `request.json()`: Die sind durch die Größenbegrenzung der Anfrage
    (16 MiB, Abschnitt 8) gedeckelt und würden die Datei in den Speicher laden. Auch die
    kleinen Textfelder liest es mit `part.read()`, das auf dieselbe Grenze trifft; sie
    sind höchstens 64 Zeichen lang und damit harmlos; **Ausnahme `name` (12.11.): höchstens 100 Zeichen, gelesen werden bis zu 400 Bytes** (mit Umlauten oder Emojis), bei Überlauf `wunsch_ungueltig`.
*   **Vor dem Körper (Schutz):** (a) Es laufen höchstens `upload_parallel` = 2 Uploads
    gleichzeitig; ein dritter bekommt 429 `zu_viele_uploads`. (b) Steht `Content-Length`
    im Kopf und übersteigt sie `upload_max_bytes`: 413 `datei_zu_gross`; übersteigt sie
    den freien Platz der Freigabe minus `UPLOAD_RESERVE_BYTES` (seit 12.11. **2 GiB** statt 100 MiB; die Bytes laufender Uploads, die noch auf ihr `Content-Length` warten, werden vom freien Platz abgezogen): 507 `kein_speicher`, beides **bevor** ein
    Byte gelesen wird.

### 5.2 Strom in Blöcken, Abschluss, Abbruch

Der Upload hat zwei Phasen mit verschiedenem Verhalten bei Abbruch (W-03).

**Phase A, Empfang** (bis zum letzten Byte des Teils `datei`):

1.  Das Backend liest den Teil `datei` in Blöcken zu **1 MiB**
    (`UPLOAD_BLOCK_BYTES = 1048576`) und schreibt jeden Block über
    `hass.async_add_executor_job` in eine **Zwischendatei**
    `medien/_upload/<16 Zeichen Zufall>.part` (gleiche Freigabe und gleiches
    Dateisystem wie der Eingang; der Name enthält **nie** die `upload_id`, damit zwei
    Uploads mit gleicher `upload_id` nie dieselbe Datei beschreiben). Die `upload_id`
    ist während des Laufs gesperrt: ein zweiter Upload mit gleicher `upload_id`, während
    der erste läuft, bekommt 409 `upload_laeuft`.
2.  Währenddessen zählt es die Bytes. Überschreitet die Datei `upload_max_bytes`
    (Vorgabe seit 12.11. 2 GiB, vorher 500 MiB; einstellbar): Abbruch, Zwischendatei löschen, 413 `datei_zu_gross`.
3.  Bricht die Verbindung ab (Handy verliert Netz, HA bricht den Handler mit
    `CancelledError` ab, weil `handler_cancellation=True`), löscht das Backend die
    Zwischendatei sofort (`except CancelledError`/`finally`). Es ist **nichts
    entstanden**. Reste (`*.part`) älter als 24 h löscht es beim Start und bei jeder
    Prüfung der Freigabe.

**Phase B, Abschluss** (ab dem letzten Byte): Alles Folgende läuft als **eigene Aufgabe,
die der Handler mit `asyncio.shield` abwartet**. Ein Abbruch des Handlers (Client
getrennt) halbiert den Abschluss deshalb nie; die Aufgabe läuft zu Ende:

1.  `fsync` und Prüfung des Formats (5.4).
2.  Unter der **Sperre des Eingangs** (Abschnitt 1): Name nach Abschnitt 12 bereinigen,
    Namensgleichheit (ohne Rücksicht auf Groß-/Kleinschreibung und Unicode-Form, W-03)
    prüfen und gegebenenfalls ` (2)` anhängen, dann die Zwischendatei **ohne
    Überschreiben** an ihren Platz bringen (`os.link` und danach `.part` löschen, oder
    Anlegen mit `O_EXCL`; **nie** ein `os.replace` auf einen vorhandenen Namen).
3.  Die Datei im Zwischenspeicher des Eingangs eintragen, `gruppe` und `serie_id` als
    Vorgabe im HA-Speicher festhalten, das **Ergebnis je `upload_id` merken** (1 Stunde,
    100 Stück, auch wenn der Client weg ist), Ereignis `upload` `fertig`, das Einsortieren
    anstoßen (5.9).
4.  Schlägt der Abschluss fehl, räumt dieselbe Aufgabe in `finally` auf (Zwischendatei
    weg) und merkt den Fehler.

Ist der Client nach Phase A weg, liegt die Datei trotzdem im Eingang. Die Seite fragt
nach einem Verbindungsfehler per `eingang/list` nach, ob die Datei da ist, und sendet
nicht blind erneut. Sendet sie doch erneut (neue `upload_id`, oder nach einem
HA-Neustart, der das gemerkte Ergebnis vergessen hat), erkennt die Einsortierung die
zweite Datei an der **Prüfsumme** und verwirft sie (11.10).

### 5.3 Eingabe und Namen

| Feld/Teil | Regel |
|---|---|
| `serie_id` (Feld) | wenn gesetzt, muss eine vorhandene Serie sein (`serie_nicht_gefunden`, 404). Die Überraschungs-Serie ist als Vorgabe erlaubt (Befüllen, D4). |
| `datei` | `filename` wird nach den **Namensregeln (Abschnitt 12)** bereinigt: verbotene Zeichen werden ersetzt (aus `Folge 1: Der Rabe.mp3` wird `Folge 1 - Der Rabe.mp3`), nichts wird abgelehnt, solange ein Name übrig bleibt. Bleibt keiner übrig: `name_ungueltig` (400). Der tatsächliche Name steht in der Antwort (`eingang_name`). |
| Endung | siehe 5.4 |
| Name vergeben | Gibt es im Eingang schon eine Datei oder einen Ordner mit dem Namen (ohne Rücksicht auf Groß-/Kleinschreibung), hängt das Backend ` (2)`, ` (3)` … an. Es gibt keinen Fehler `datei_existiert` mehr (Vorgabe der Projektleitung 09.11.). Dieselbe Datei zweimal wird später an der Prüfsumme erkannt (11.10). |
| `upload_id` | verbindet die Anfrage mit den Ereignissen (4.7) und macht eine Wiederholung unschädlich (5.6) |

### 5.4 Formate und Prüfung (D5)

*   **Erlaubte Endungen** (ohne Unterscheidung von Groß- und Kleinschreibung), die Liste
    aus `data-model.md`, Abschnitt 5: `mp3`, `m4a`, `m4b`, `aac`, `flac`, `ogg`,
    `opus`, `wav`. Jede andere Endung: 415 `format_nicht_erlaubt`, noch **bevor** der
    Körper gelesen wird, wenn die Endung schon im ersten Teil steht (sonst nach
    dem Strom).
*   **Inhalt, `ffprobe` als Pflicht-Härtung (W-16):** Das Backend öffnet die fertige
    Zwischendatei mit `ffprobe` (im Executor). Der Aufruf **muss** so aussehen:
    *   als **Liste von Argumenten** (`asyncio.create_subprocess_exec` bzw.
        `subprocess.run([...])`), nie über eine Shell, der Dateiname nie in einer
        Shell-Zeile; der Pfad wird als `file:<absoluter Pfad>` übergeben (ein Name mit
        führendem `-` ist so keine Option);
    *   mit `-v error -protocol_whitelist file -print_format json -show_format
        -show_streams` (Tags stehen in `format.tags` und `streams[].tags`). **(09.11., Befund AP 3.1)**
        `ffprobe` kennt `-nostdin` nicht (nur `ffmpeg`; „Option not found“). Die Integration schließt
        stattdessen die Standardeingabe (`stdin=DEVNULL`). `-nostdin` bekommt nur `ffmpeg` bei der
        Probedekodierung (1 s);
    *   mit **erzwungenem Format** aus der Endung (`-f mp3`, `-f mov,mp4,m4a,3gp,3g2,mj2`
        für `m4a`/`m4b`, `-f aac`, `-f flac`, `-f ogg` für `ogg`/`opus`, `-f wav`); das
        Probieren aller Formate entfällt;
    *   mit **Zeitlimit 30 s** und **Speicherlimit** (`RLIMIT_AS` 1 GiB, soweit das System
        es erlaubt) und mit abgebrochenem Prozess bei Überschreitung;
    *   danach prüft das Backend `format.format_name` gegen die erlaubte Liste und verlangt
        **mindestens einen Audio-Strom**. Playlist-Formate (`hls`, `concat`, `m3u8`, `sdp` …)
        und alles, was nicht auf der Liste steht, lehnt es ab: 415 `format_nicht_erlaubt`.
        **Textdatei und Defekt (09.11., Befund AP 3.1):** Scheitert `ffprobe` und die Datei sieht
        aus wie Text (in den ersten 8 KiB **kein NUL-Byte** und mindestens 95 % druckbare Zeichen),
        ist es das falsche Format: 415 `format_nicht_erlaubt` (z. B. eine Textdatei oder Playlist mit
        Endung `.mp3`). Scheitert `ffprobe` an einer Binärdatei (NUL-Byte oder kaum Text), ist sie
        defekt: **kein 415**, nur die Warnung `nicht_lesbar` (nächster Punkt).
*   **Kopierschutz und Defekte** (D5; Entscheidung M, Vorgabe 8) führen im Upload **nicht
    zur Ablehnung**, sondern zur **Warnung**: Die Datei kommt in den Eingang und **bleibt
    dort** (Abschnitt 11.10), sie kommt nicht in die Medien. Warngründe: `kopierschutz`
    (Codec `drms`), `nicht_lesbar` (`ffprobe` scheitert), `probedekodierung_fehlgeschlagen`
    (Probedekodierung von 1 s). Fehlt `ffprobe` in HA, ist das Ergebnis
    `pruefung="nicht_moeglich"`; die Datei bleibt im Eingang (`ffprobe_fehlt`, ohne
    `ffprobe` gibt es auch keine Tags).
*   Lautheit (D6) misst der Container auf dem NAS **später**; sie ist kein Teil des
    Uploads.

### 5.5 Ausgabe

Erfolg: HTTP 200, `Content-Type: application/json`.

```json
{
  "v": 1,
  "upload_id": "9b6c0f7e-3b52-4d1a-9c58-0e2b7a41d9f3",
  "eingang_name": "Folge 4 - Der Rabe.mp3",
  "serie_id": "3f9a1c07b2d4",
  "groesse_bytes": 48210433,
  "pruefung": "ok",
  "hinweis": null,
  "wiederholt": false
}
```

`pruefung` ∈ `ok`, `warnung`, `nicht_moeglich`; `hinweis` ist ein Code (siehe 3.9) oder
`null`; `serie_id` ist die Vorgabe oder `null`; `wiederholt=true` heißt, die Antwort
gehört zu einer früheren Anfrage mit derselben `upload_id` (5.6). Wohin die Datei
einsortiert wird, steht erst nach dem Einsortieren fest (Ereignis `eingang`
`neu_einsortiert`, Befehl `eingang/list`). Fehler: HTTP-Status wie in Abschnitt 7 und der
Körper

```json
{ "v": 1, "fehler": { "code": "format_nicht_erlaubt", "text": "Dieses Dateiformat spielt die Box nicht." } }
```

### 5.6 Idempotenz

Der Upload ändert den Zustand (eine neue Datei). Sendet die Seite dieselbe Datei mit
**derselben `upload_id`** noch einmal (z. B. weil die Antwort verloren ging) und der
Abschluss war erfolgreich, antwortet das Backend mit dem alten Ergebnis
(`wiederholt=true`) und nimmt nichts doppelt auf (es merkt sich die letzten 100
`upload_id` für 1 Stunde im Arbeitsspeicher, **auch wenn der Client weg war**, 5.2).
Ohne `upload_id` oder mit neuer: Die Datei kommt noch einmal in den Eingang (Suffix) und
wird beim Einsortieren als Duplikat erkannt und verworfen (11.10). Ein in Phase A
abgebrochener Versuch hinterlässt keine Datei, ein Neustart des Uploads ist also immer
sicher (Fortsetzen eines halben Uploads gibt es in Version 1 nicht).

### 5.7 Fortschritt

Die Seite sendet mit `XMLHttpRequest` und misst das Senden mit `upload.onprogress`
(`fetch` kann den Fortschritt beim Hochladen nicht melden). Nach dem letzten Byte
läuft die Prüfung auf dem Backend; dafür gibt es das Ereignis `upload` (4.7). Die
HTTP-Antwort kommt erst nach dem Abschluss (Prüfung bis 30 s). Ein Ereignis `empfange`
gibt es nicht.

### 5.8 Was dieser Vertrag nicht regelt

*   Fortsetzen halber Uploads (Wiederaufnahme), parallele Übertragung einer Datei in
    mehreren Teilen.
*   Ein **Folgen-Ordner** (mehrere Tracks) entsteht beim Upload nur über die Tags:
    Dateien mit gleichem Album und gleicher `gruppe` werden zu einem Folgen-Ordner
    (11.3). Eine Nachlieferung einzelner Tracks zu einer schon einsortierten Folge gibt es
    in Version 1 nicht (11.3).
*   Ob Nabu Casa sehr große Anfragen und lange Übertragungen durchlässt: unbekannt, wird
    bei der Abnahme am Handy mit drei Größen gemessen (Abschnitt 8, offener Punkt 1).

### 5.9 Einsortieren nach dem Upload

Nach dem Abschluss wartet das Backend `UPLOAD_SAMMELZEIT_S` = 20 s ab dem **letzten**
Upload-Abschluss (damit die Dateien einer `gruppe` zusammen sortiert werden) und startet
dann einen Durchlauf. Die Ruhezeit von 120 s (11.1) gilt für hochgeladene Dateien nicht,
weil sie vollständig sind.

## 6. Abläufe

### 6.1 Neuer Tobie, Weg A (CUJ 7a, 12)

1.  Eine Box meldet eine Kennung (`…/unknown/<uid>`). Ist sie schon zugeordnet, bestätigt
    das Backend mit `bekannt` und nimmt sie nicht auf (3.4). Sonst nimmt es sie in
    „Neue Tobies“ auf, bestätigt auf `…/ack` (`neu` oder `bekannt`) und sendet das
    Ereignis `neue_tobies` (`neu`/`aktualisiert`).
2.  Die Seite zeigt den Eintrag (`neue_tobies/list`). Tobias wählt den Typ (Serie oder
    einzelne Folge, bei Folge die Folge) oder eine Aktionskarte, gibt dem Tobie auf
    Wunsch einen Namen und tippt.
3.  Die Seite sendet `zuordnung/set` (mit `erwartet_ziel: null`). Das Backend schreibt die
    Zuordnung, erhöht die Revision, veröffentlicht `tobibox/config`, entfernt den
    Eintrag aus der Liste. Die Box übernimmt die Liste und wechselt, wenn der Tobie
    noch liegt, auf das Ziel.
4.  Tobias kann statt dessen `neue_tobies/verwerfen` aufrufen.
5.  **Seit 13.11. (Weg 2 „Später auflegen“):** Wartet in Schritt 1 für diese Box eine passende Vormerkung (3.13), nimmt das Backend die Kennung nicht in „Neue Tobies“ auf, ordnet sofort zu (Revision + 1, `tobibox/config`), trägt die Vormerkung aus, bestätigt mit `bekannt` und meldet `warteschlange` `abgearbeitet`. Die Schritte 2 und 3 entfallen; die Seite zeigt „Name geben“.

### 6.2 Lernmodus, Weg B (CUJ 7b)

*Seit 13.11. nur für Administratoren (X13a); der Alltag benutzt die Warteschlange, 3.13 (Zusammenspiel: Regel 9).*

Reihenfolge wie in `mqtt-v1.md`, 4.2. Fett die Befehle dieser Schnittstelle. Alle
Wege, die eine Zuordnung schreiben (Seite, Aktion, `ui/*`), laufen durch dieselbe
Funktion (Abschnitt 1).

1.  Die Seite sendet **`lernmodus/start`** (Box, Typ, Ziel). Das Backend merkt sich Box,
    Ziel, Beginn und `befehl_id` und sendet `cmd` `lernen` (`ttl_s` 60). Ereignis
    `lernmodus` `wartet`. Sieht das Backend einen Status der Box mit `lernmodus=true`,
    merkt es sich das für den Vorgang (Voraussetzung für das Ende nach Punkt 6).
2.  Die Box lernt höchstens 2 min und meldet einen aufgelegten Tobie als
    `art="gelernt"` mit `befehl_id` auf `…/unknown/<uid>`.
3.  Das Backend sucht den Vorgang mit dieser `befehl_id` und prüft die Fristen. Ein
    Vorgang, der für die Seite schon `abgelaufen` ist (3.6, „tot“), nimmt die **späte**
    Meldung bis `frist_bis` trotzdem noch an (Funkstörung, Statusreihenfolge).
    *   **Kein Vorgang oder `frist_bis` vorbei** (auch nach **`lernmodus/abbrechen`**):
        `ack` mit `grund="abgelehnt"`, keine Konfiguration. Die Box meldet den Tobie als
        unbekannt erneut; er erscheint in „Neue Tobies“.
    *   **Nach einem HA-Neustart** (der Vorgang ist im Arbeitsspeicher weg): Die letzten
        **20** abgeschlossenen Vorgänge (`befehl_id`, Ergebnis, `uid`, Ziel) stehen im
        HA-Speicher (W-08). Kommt dieselbe `befehl_id` mit einem Ergebnis `zugeordnet`
        erneut (retained-Zustellung, QoS 1), stellt das Backend sicher, dass die aktuelle
        Konfiguration veröffentlicht ist (PUBACK) und wiederholt das `ack zugeordnet`. Steht
        das Ergebnis `abgelehnt` dort, wiederholt es `abgelehnt`. Ist die `befehl_id` ganz
        unbekannt: `abgelehnt`.
    *   **Kennung noch nicht zugeordnet:** weiter bei 4.
    *   **Kennung schon mit genau diesem Ziel (und diesem Namen, falls gesetzt):** keine
        neue Revision. Das Backend sendet `ack` mit `grund="abgelehnt"` (die Box beendet
        das Warten sofort und spielt wie beim normalen Auflegen das bestehende Ziel,
        also dasselbe; keine 10 s Stille, W-07 d) und meldet das Ereignis `lernmodus`
        `zugeordnet` mit `grund="unveraendert"` und dem Text „Der Tobie hat dieses Ziel
        schon.“ (kein `abgelehnt`-Zustand, weil für Tobias nichts schiefging).
    *   **Kennung schon mit anderem Ziel zugeordnet:** Ereignis `lernmodus` `rueckfrage`
        (mit `uid`, `bisher`, `ziel`, `rueckfrage_bis`) und eine HA-Benachrichtigung
        (`persistent_notification`; sie bleibt, bis die Rückfrage beantwortet ist oder
        abläuft; W-09). Die Seite fragt Tobias und sendet **`lernmodus/antwort`**.
        **`rueckfrage_bis` = das spätere von `frist_bis` und Eingang der Meldung + 60 s**
        (die Frist des Vorgangs bleibt 180 s, Vorgabe der Projektleitung; dazu eine
        Mindestzeit von 60 s zum Antworten). Bei `ueberschreiben=false` oder wenn bis
        `rueckfrage_bis` keine Antwort kommt (auch ohne offene Seite): `ack` `abgelehnt`,
        Ende. Bei `true`: weiter bei 4. Bei einer Aktion ohne Seite gilt
        `ueberschreiben=false`, es sei denn, das Aktionsfeld sagt `true` (Abschnitt 1).
4.  Das Backend schreibt die Zuordnung (Revision + 1) und veröffentlicht `tobibox/config`.
    **Erst nach dem PUBACK** der Konfiguration sendet es das `ack`
    `grund="zugeordnet"` (Entscheidung H, W-07 a): Zwei getrennte Veröffentlichungen
    behalten bei QoS 1 ihre Reihenfolge bei Neuübertragung nicht garantiert. **Ohne PUBACK
    (Broker weg) kein `ack`**: Der Vorgang bleibt `wartet` mit gespeicherter Zuordnung; die
    Meldung auf `…/unknown/<uid>` bleibt retained, und das Backend holt Veröffentlichung
    und `ack` beim Wiederverbinden nach, solange `frist_bis` nicht vorbei ist; danach
    `abgelehnt`. Entfernt die Kennung aus „Neue Tobies“. Ereignis `lernmodus` `zugeordnet`.
    **Fehlerwege (W-07 c):** Scheitert Schritt 4, bevor etwas gespeichert ist, sendet das
    Backend `ack` `abgelehnt` (nichts geändert, Klartext im Ereignis) mit einem `grund`:
    `konfig_zu_gross` (256 KiB), `speicherfehler` (HA-Speicher nicht schreibbar),
    `ziel_fehlt` (die Serie oder Folge gibt es inzwischen nicht mehr),
    `konfig_nicht_bereit` (Zustand der Konfiguration nicht `ok`).
5.  Braucht Tobias für die Rückfrage länger als 10 s, spielt ein bekannter Tobie
    zuerst sein altes Ziel und wechselt mit der Zuordnung (gewollt, Entscheidung H,
    `mqtt-v1.md`, 4.2).
6.  **Der Vorgang endet sauber (W-05):** Er endet mit genau einem Zustand aus
    `zugeordnet`, `abgelehnt`, `abgebrochen`, `abgelaufen`, `box_lehnt_ab`. `abgelaufen`
    folgt, sobald (a) ein Status mit `lernmodus=false` nach einem Status mit
    `lernmodus=true` eintrifft (`grund="box_beendet"`), oder (b) 30 s nach `beginn` kein
    Status mit `lernmodus=true` gesehen wurde (`grund="kein_status"`), oder (c) `frist_bis`
    vorbei ist (`grund="frist"`). Lehnt die Box den Befehl ab (`befehl_abgelehnt`), endet
    er mit `box_lehnt_ab`. Ein beendeter Vorgang verschwindet aus `boxen/list`
    (`lernmodus=null`) und steht in den letzten 20 abgeschlossenen. Ein erneuter Start
    erzeugt einen neuen Befehl (3.6).

### 6.3 Medien (CUJ 9)

Serien anlegen, umbenennen, sortieren, verschieben, zusammenführen, löschen und
Hochladen schreiben nur auf die Freigabe. Die Box holt sie mit dem Sync. Es gibt keine
MQTT-Nachricht und keine Revision, **außer** wenn eine Korrektur Tobies auf ein neues
Ziel umschreibt (Nr. 26, 27). Die Seite bietet nach einer Änderung „Sync jetzt“ an
(`box/sync`).

**Löschen mit Tobies (Vorgabe der Projektleitung 09.11.):** Die Seite liest vor dem
Löschen einer Folge oder Serie `serie/get` und zeigt, wenn Tobies darauf zeigen,
Anzahl und **Namen** (bzw. gekürzte Kennungen) mit der Rückfrage „N Tobies zeigen
darauf: … Trotzdem in den Papierkorb?“. Erst die Bestätigung sendet den Befehl mit
`tobies_bestaetigt=true`. Die Zuordnung bleibt; die Box spielt bis zur
Wiederherstellung die Überraschung.

### 6.4 Hochladen vom Handy (CUJ 9)

1.  Die Seite wählt die Dateien, auf Wunsch die Serie (Vorgabe, 11.5), erzeugt je Datei
    eine `upload_id` und für zusammengehörige Dateien (ein Hörbuch aus mehreren Dateien)
    eine gemeinsame `gruppe`.
2.  Sie holt ein frisches Token, sendet nacheinander je Datei `POST …/upload` und
    zeigt den Fortschritt (5.7).
3.  Die Antwort liefert `pruefung`; bei `warnung` zeigt die Seite den Grund und dass
    die Datei im Eingang bleibt.
4.  Das Backend sortiert nach 20 s Sammelzeit ein (5.9); Ereignis `eingang`
    `neu_einsortiert` zeigt, wohin die Datei kam und ob „bitte prüfen“ gesetzt ist.
    `medien` `serien_geaendert` lässt andere offene Fenster neu laden.

### 6.5 Einsortieren vom PC (Entscheidung M)

1.  Tobias legt einen Ordner (z. B. einen Hörbuch-Download) oder Dateien in
    `tobibox/eingang/`.
2.  Der nächste Durchlauf (Timer alle 10 min, Öffnen der Seite oder `eingang/sortieren`)
    findet den Eintrag; solange er sich noch ändert, steht er auf `wartet`.
3.  Nach der Ruhezeit liest das Backend die Tags, gruppiert zu Alben, bestimmt Serie,
    Reihenfolge und Namen (Abschnitt 11), legt Serien und `serie.json` an bzw. ergänzt
    sie und verschiebt die Dateien.
4.  Ereignis `neu_einsortiert` je Eintrag; die Seite zeigt unter „Eingang“ das
    Ergebnis, Folgen mit „bitte prüfen“ sind markiert.
5.  Tobias korrigiert bei Bedarf: Serie wechseln (`folge/verschieben`), Namen ändern
    (`serie/rename`, `folge/rename`), Reihenfolge ändern (`folgen/order`), zwei Serien
    zusammenführen (`serien/zusammenfuehren`), und bestätigt (`einsortierung/bestaetigen`).
6.  Blockiertes (Kopierschutz, defekt) bleibt im Eingang mit Hinweis (11.10).

## 7. Gemeinsame Fehlercodes

Die Codes `invalid_format`, `unauthorized`, `unknown_command`, `unknown_error` sind
die von **Home Assistant**; alle anderen sind eigene Codes dieses Vertrags. Bei
WebSocket-Befehlen steht der Code in `error.code`; HA kennt im Fehlerobjekt nur `code` und
`message`. **Maschinenlesbare Einzelheiten stehen deshalb nie nur in `message`:**
Die Seite liest bei Bedarf den Zustand neu (z. B. `zuordnung/list` nach
`zuordnung_existiert`, `serie/get` nach `tobies_betroffen`).

| Code | HTTP | Bedeutung | Befehle |
|---|---|---|---|
| `invalid_format` | 400 | Eingabe passt nicht zum Schema (fehlendes Pflichtfeld, falscher Typ, unbekanntes Feld, `bestaetigt` nicht `true`) | alle |
| `unauthorized` | 401 oder 403 | Nutzer ist kein Administrator (seit 13.11. auch bei `lernmodus/start`, `lernmodus/antwort`, `lernmodus/abbrechen`), oder (seit 12.11.) eine Schutzregel für Nicht-Administratoren greift (2.4: fehlendes `erwartet_ziel`, `sofort`, `lesezeichen_tage`). Bei WebSocket gilt der Code; die Seite wertet `code` aus. Der Upload prüft keine Administratorrolle mehr (W-19 entfällt). | alle mit Recht `admin` und die Schutzregeln in 2.4 |
| `unknown_command` | – | Befehl dem Backend unbekannt (Seite neuer als Backend) | alle |
| `unknown_error` | 500 | Fehler im Backend (Fehler im Protokoll von HA); die Seite zeigt „Das hat nicht geklappt“ | alle |
| `anfrage_id_konflikt` | 409 | gleiche `anfrage_id` mit anderem Befehl oder anderen Feldern | die mit `anfrage_id` |
| `medien_nicht_erreichbar` | 503 | Die NAS-Freigabe ist nicht eingebunden oder antwortet nicht | Medien, Eingang, Papierkorb, Upload, Export |
| `medien_schreibfehler` | 500 | Schreiben auf die Freigabe schlug fehl (Rechte, Platz, Verbindung, Namen, die die Freigabe nicht annimmt) | Medien, Eingang, Papierkorb |
| `kein_speicher` | 507 | Auf der Freigabe ist kein Platz mehr (vorab geprüft, 5.1; seit 12.11. auch Kontingent von `hoerkopien/`, 14.8) | Upload, Hörkopie |
| `mqtt_nicht_verbunden` | 503 | Der Broker ist nicht erreichbar; der Befehl wurde **nicht** gesendet. (Konfigurationsänderungen scheitern daran nicht: Sie sind gespeichert, `veroeffentlicht=false`.) | Befehle an Boxen |
| `serie_nicht_gefunden` | 404 | Serien-ID unbekannt | Serie, Folgen, Upload, Zuordnung, Lernmodus, Papierkorb, Warteschlange |
| `folge_nicht_gefunden` | 404 | Folge steht nicht in `folgen` der Serie | Folgen, Zuordnung, Lernmodus, Warteschlange |
| `eintrag_nicht_gefunden` | 404 | Papierkorb-Eintrag oder Eingangs-Eintrag unbekannt | Papierkorb, Eingang |
| `export_nicht_gefunden` | 404 | Es gibt keine Exportdatei | `konfig/aus_export` |
| `export_ungueltig` | 422 | Die Exportdatei ist nicht lesbar oder nach `data-model.md` ungültig; nichts wurde übernommen | `konfig/export_lesen`, `konfig/aus_export` |
| `box_unbekannt` | 404 | Box-Name ist nicht eingerichtet | Boxen, Lernmodus, Warteschlange, `zuordnung/remove` (mit `als_neu`) |
| `box_offline` | 409 | Die Box ist nach `…/online` nicht erreichbar oder HA kennt noch keine Nachricht (`online=null`, W-25) | `lernmodus/start`, `box/sync` |
| `kennung_ungueltig` | 400 | `uid` ist nicht kanonisch (`reader-v1.md`, Abschnitt 4) | Zuordnung, Neue Tobies |
| `ziel_ungueltig` | 400 | `ziel` ist unvollständig oder widersprüchlich (z. B. `folge` ohne `serie`, unbekannte `aktion`, `aktion` im Lernmodus), **zeigt auf die Überraschungs-Serie**, oder Quelle und Ziel sind dieselbe Serie / eine Überraschungs-Serie beim Zusammenführen | Zuordnung, Lernmodus, Warteschlange, `folge/verschieben`, `serien/zusammenfuehren` |
| `zuordnung_existiert` | 409 | Die Kennung hat schon ein anderes Ziel, `ueberschreiben` fehlt | `zuordnung/set` |
| `zuordnung_geaendert` | 409 | `erwartet_ziel` stimmt nicht mehr (ein anderes Fenster hat die Zuordnung geändert); die Seite lädt neu | `zuordnung/set`, `zuordnung/remove` |
| `konfig_zu_gross` | 413 | Die Konfiguration würde 256 KiB überschreiten (`mqtt-v1.md`, Abschnitt 1) | `zuordnung/set`, `lernmodus/antwort` |
| `konfig_nicht_bereit` | 409 | `konfig.zustand` ist nicht `ok` (Abschnitt 13); die Seite zeigt die Warnung | alle, die die Konfiguration ändern, und `warteschlange/set` |
| `name_ungueltig` | 400 | Name leer, zu lang oder nach der Bereinigung (Abschnitt 12) leer | Serie, Folge, Tobie-Name, Warteschlange (`name`, K7), Upload |
| `reihenfolge_ungueltig` | 400 | Die Liste ist keine Umstellung der vorhandenen Folgen | `folgen/order` |
| `stand_veraltet` | 409 | `stand` passt nicht mehr; die Seite lädt neu | alle mit `stand` |
| `tobies_betroffen` | 409 | Tobies zeigen auf das, was gelöscht oder verschoben wird, und `tobies_bestaetigt` fehlt; die Seite fragt Tobias und liest `serie/get` | `folge/delete`, `serie/delete`, `folge/verschieben`, `serien/zusammenfuehren` |
| `ueberraschung_existiert` | 409 | Es gibt schon eine Überraschungs-Serie | `serie/create` |
| `lernmodus_laeuft` | 409 | Für die Box läuft ein lebender Lernmodus mit anderem Ziel; erst abbrechen | `lernmodus/start` |
| `kein_lernmodus` | 404 | Kein offener Vorgang mit dieser `befehl_id` | `lernmodus/antwort` |
| `rueckfrage_abgelaufen` | 409 | `rueckfrage_bis` ist vorbei; das Backend hat die Meldung abgelehnt | `lernmodus/antwort` |
| `datei_existiert` | 409 | Im Serien-Ordner gibt es den Namen schon | `papierkorb/restore` (Folge) |
| `serie_existiert` | 409 | Die Serien-ID ist schon vergeben | `papierkorb/restore` (Serie) |
| `upload_laeuft` | 409 | Ein Upload mit dieser `upload_id` läuft noch | Upload |
| `zu_viele_uploads` | 429 | Es laufen schon `upload_parallel` Uploads | Upload |
| `datei_zu_gross` | 413 | größer als `upload_max_bytes` (seit 12.11. Vorgabe 2 GiB) oder, bei Cover, als `COVER_UPLOAD_MAX_BYTES` | Upload, Cover |
| `format_nicht_erlaubt` | 415 | Endung oder erkanntes Format nicht nach D5 | Upload |
| `einstellung_ungueltig` | 400 | Eine Einstellung ist nach `data-model.md`, Abschnitt 2, ungültig (Wertebereich, Typ, doppelte `id` …); nichts wurde geändert. Die Stelle steht in `message` (3.11) | `einstellungen/set` |
| `sortierung_laeuft` | 409 | Ein Durchlauf des Einsortierens läuft; der Eintrag lässt sich jetzt nicht entfernen. Später noch einmal versuchen. | `eingang/entfernen` |
| `zu_viele_aenderungen` | 429 | **(12.11.)** Eine Menge aus 2.4 ist überschritten (Änderungen der Liste, Papierkorb-Aktionen, Upload-Bytes je Stunde, Cover je Stunde, `hoerstelle/set`, `audio/bereit`, seit 13.11. `warteschlange/set` und `warteschlange/abbrechen`). Kurz warten. | Befehle mit Menge, Upload, Cover |
| `cover_ungueltig` | 400 | **(12.11.)** Das Bild ist kein gültiges JPEG, nicht quadratisch genug oder zu groß in Pixeln (14.3) | Cover (POST) |
| `cover_nicht_gefunden` | 404 | **(12.11.)** Der Eintrag hat kein Cover | Cover (GET) |
| `wunsch_ungueltig` | 400 | **(12.11.)** Pflichtfelder des Upload-Wunsches fehlen oder passen nicht zusammen (14.4), `name` über 400 Bytes | Upload, `einsortierung/neu` |
| `neu_einsortieren_nicht_moeglich` | 409 | **(12.11.)** Der Eintrag ist nicht mehr „bitte ansehen“ oder jünger als 24 Stunden, oder an seinen Folgen wurde schon etwas geändert (2.4) | `einsortierung/neu` |
| `hoerkopie_warteschlange_voll` | 429 | **(12.11.)** Die Warteschlange der Hörkopien hat ihre Grenze (14.8) | `audio/bereit`, `hoerkopie/neu_erzeugen` |
| `zu_viele_streams` | 429 | **(12.11.)** Der Benutzer hat schon `AUDIO_VERBINDUNGEN_JE_BENUTZER` offene Audio-Verbindungen | Audio (HTTP) |
| `warteschlange_voll` | 409 | **(13.11.)** Es warten schon `WARTESCHLANGE_MAX` (5) Vormerkungen; die Seite sagt: „Es warten schon 5 Tobies. Warte, bis einer aufgelegt ist, oder nimm einen aus der Liste.“ | `warteschlange/set` |
| `warteschlange_doppelt` | 409 | **(13.11.)** Genau diese Vormerkung (gleiche Box, gleiches Ziel) wartet schon; die Seite sagt: „Das wartet schon.“ | `warteschlange/set` |
| `hoerkopie_wartet` | 503 | **(12.11.)** Die Hörkopie wird noch erzeugt (nur HTTP, mit `Retry-After: 60`; Rückfall für Aufrufer ohne `audio/bereit`) | Audio (HTTP) |

Der Körper einer HTTP-Fehlerantwort des Uploads ist in 5.5 beschrieben. Eine
unbekannte `code`-Zeichenfolge (neueres Backend) zeigt die Seite mit `message`
beziehungsweise `fehler.text`.

## 8. Grenzen

Aus dem Quelltext von Home Assistant (Zweig `dev`, abgerufen am 09.11.2026; **maßgeblich ist die
feste HA-Version** der Stufe 3a, **2026.11.x**, die genaue Patch-Version nennt Tobias beim
Start von AP 3.1) und aus dem Design:

| Grenze | Wert | Quelle und Folge |
|---|---|---|
| Größe einer **eingehenden** WebSocket-Nachricht | 4 MiB (Vorgabe von aiohttp; HA setzt `WebSocketResponse(heartbeat=55, …)` ohne eigenen Wert) | Darum **keine** Dateien über WebSocket, sondern HTTP (Abschnitt 5). Eingaben dieses Vertrags sind klein (wenige KiB). |
| Größe einer Nachricht, die dieser Vertrag **sendet** | höchstens 64 KiB (wie `mqtt-v1.md`) | In HA gibt es keine feste Grenze für ausgehende Nachrichten (nur die Warteschlange); 64 KiB ist die eigene Wahl dieses Vertrags. Alle Listen blättern deshalb mit `limit`/`offset`: `neue_tobies/list`, `papierkorb/list` (höchstens 200 Einträge ≈ 50 KiB), `zuordnung/list` (höchstens 100 Einträge ≈ 35 KiB, W-13), `eingang/list` (höchstens 100). `serien/list` und `boxen/list` sind durch die Anzahl der Serien bzw. Boxen klein. |
| Nachrichten je Verbindung, bis HA sie trennt | 4096 wartende Nachrichten (`MAX_PENDING_MSG`) | Ereignisse sind gebündelt (4). |
| Lebenszeichen der WebSocket-Verbindung | 55 s (`heartbeat`) | von HA, nichts zu tun |
| Anmeldung | Die Verbindung muss die Authentifizierung (`auth`) innerhalb weniger Sekunden schicken | macht `hass.connection` der Oberfläche |
| Normale HTTP-Anfragen von HA | **16 MiB** | **Belegt (W-14):** `homeassistant/components/http/server.py`, Zeile 69 `MAX_CLIENT_SIZE: Final = 1024**2 * 16`, benutzt in Zeile 278 (`client_max_size=MAX_CLIENT_SIZE`); Forenmeldung zu 2026.7/2026.8 „Maximum request body size 16777216 exceeded“ (Issue #177999, „not a bug“). Die Grenze gilt für `read()`, `post()`, `json()` und `part.read()`, **nicht** für das Lesen mit `request.multipart()` und `part.read_chunk()`. HA-eigene Uploads setzen die Grenze je Ansicht (`file_upload` 100 MiB, `media_source` 20 MiB); `HomeAssistantView.max_body_size` (`helpers/http.py`, Zeile 139) wirkt vor dem Handler. Der Upload setzt es **nicht** und streamt. AP 3.1 belegt es mit einem Test über 16 MiB (z. B. **40 MiB**) gegen die feste HA-Version und deren aiohttp. |
| Größe einer Audiodatei | `upload_max_bytes`, Vorgabe seit 12.11. **2 GiB** (`UPLOAD_MAX_MIB_VORGABE` 2048; vorher 500 MiB), in der Einrichtung der Integration einstellbar. Ein bestehender Konfigurationseintrag mit 500 wird beim Update auf 2 048 angehoben. (Entscheidung Tobias, Runde 10: Hörbücher gehen vom Handy; 12 Stunden M4B bei 128 kbit/s sind etwa 690 MiB.) | Schutz vor vollem Speicher und langen Übertragungen über Nabu Casa. Der Stream schreibt in Blöcken, es entsteht kein Speicherproblem; die Zwischendatei wächst bis 2 GiB. |
| Gleichzeitige Uploads | 2 (`upload_parallel`) | 429 `zu_viele_uploads` |
| Freier Platz vor dem Upload | `Content-Length` + `UPLOAD_RESERVE_BYTES` (seit 12.11. **2 GiB** Reserve statt 100 MiB) gegen den freien Platz der Freigabe **minus** der noch nicht übertragenen Bytes laufender Uploads | 507 `kein_speicher` vor dem Lesen; Test: zwei Uploads von 2 GiB bei Platz für einen, der zweite bekommt `kein_speicher` |
| Upload je Stunde und Benutzer | 16 GiB (`UPLOAD_BYTES_JE_STUNDE`, seit 12.11.) | `zu_viele_aenderungen` |
| Weitere Mengen und Grenzen der Stufe A | Abschnitt 14.10 (Cover, Audio, Hörstelle, Hörkopie; Hörkopie-Grenzen **vorläufig, nach Messung A0b**) | |
| Block des Uploads | 1 MiB | fest in Version 1 |
| Zugriffstoken | gültig ~30 min | gilt für den **Start** einer Anfrage; die Seite erneuert vor jedem Upload. |
| Länge eines Namens | Serie 1–100 Zeichen; Folge-Anzeige 1–200 Zeichen; Tobie-Name 1–60 Zeichen; Datei- und Ordnername höchstens 255 Bytes (UTF-8) **und** 255 UTF-16-Einheiten, die kürzere Grenze gilt (Abschnitt 12) | `data-model.md` |
| Ruhezeit im Eingang | 120 s (`EINGANG_RUHE_S`); Sammelzeit nach Upload 20 s (bei Uploads mit `gruppe_anzahl` wartet der Eingang auf alle Dateien, höchstens `GRUPPE_RUHE_MAX_S` = 30 Minuten Ruhe, 14.4) | Abschnitt 11.1, 5.9 |
| Nabu Casa | unbekannt (Upload-Größe, Dauer) | **Abnahme am Handy mit vier Größen: 20 MiB, 150 MiB, 500 MiB und 2 GiB, jeweils mit gemessener Dauer** (seit 12.11.; vorher drei Größen bis 500 MiB; Messung A0b und Abnahme A-1). Ausweg: Dateien per PC in den Eingang (D4, Entscheidung M). |

## 9. Versionierung

*   **Version 1** ist diese Fassung. Sie steht in `hello` (`v`) und in jedem
    Ereignis und jeder HTTP-Antwort des Uploads (`"v": 1`).
*   **Ohne Erhöhung** erlaubt: neue Befehle (neue Namen), neue **optionale**
    Eingabefelder, neue Felder in Ausgaben und Ereignissen, neue `art`-Werte, neue
    Themen, neue Hinweis-Codes, neue Fehlercodes für neue Fälle, neue Werte in
    `faehigkeiten`. Die Seite ignoriert Unbekanntes in Antworten und Ereignissen.
*   **Eingaben sind strenger.** Der HA-Schemaprüfer lehnt **unbekannte Eingabefelder
    ab** (`invalid_format`). Eine neue Seite darf deshalb ein neues optionales
    Eingabefeld nur senden, wenn `hello.faehigkeiten` es zusagt. Seite und Backend
    liegen im selben Paket (`custom_components/tobibox/`), und die Adresse der Seite
    trägt die Version der Integration (`/tobibox_static/tobibox-panel.js?v=<version>`), um
    den Browser-Zwischenspeicher zu umgehen; das Problem entsteht nur bei einer
    alten Seite im Zwischenspeicher.
*   **Erhöhung** von `v` bei: Befehl, Feld oder Code entfernt oder umbenannt,
    Bedeutung oder Wertebereich geändert, neues **Pflichtfeld**. Dann bekommt die neue
    Hauptversion einen **neuen Wurzelnamen** für die Befehle (`tobibox2/…`) und läuft
    neben der alten, bis die Seite umgestellt ist (wie `mqtt-v1.md`, Abschnitt 8). Der
    HTTP-Pfad erhält `/api/tobibox2/…`.
*   **Prüfung beim Start:** Die Seite ruft zuerst `tobibox/hello` mit ihrem `v`. Ist
    das `v` der Antwort **kleiner** als das der Seite, oder kommt `unknown_command`,
    zeigt sie „Bitte die Seite neu laden (Strg+F5)“ und tut nichts weiter. Ist es
    **größer**, kennt die Seite nur ihre eigene Version (die alte Befehlsgruppe läuft
    weiter, solange das Backend sie noch anbietet).
*   Eine Änderung dieses Vertrags geht an die Projektleitung. Backend und Seite ändern
    sie nicht eigenmächtig.


## 10. Später (Namen reserviert, Inhalt noch nicht festgelegt)

Diese Befehle gehören **nicht** zu Version 1 der Stufe 3a. Ihre Namen sind vergeben;
die Eingabe, Ausgabe und Fehler stehen fest, sobald die Stufe beginnt. Sie brauchen
nur Ergänzungen (Abschnitt 9, „Ohne Erhöhung“). (`serie/delete` und `folge/rename`
sind seit dem 09.11. Teil von Version 1: Nr. 24 und 25. **`einstellungen/get` und
`einstellungen/set` sind seit dem 09.11. (AP 4.7) gültig: Nr. 35 und 36, Abschnitt 3.11.**)

| Befehl | Stufe | Skizze (Vorschlag, keine Festlegung) |
|---|---|---|
| `tobibox/box/update` | 3b (AP 3.8/3.11) | `{"box", "version"?}`; Backend nimmt ohne Angabe die neueste Version aus `releases/`. Rechte: Admin. MQTT: `cmd` `update`, 300 s (`mqtt-v1.md`, 3.7). Ergebnis über `status.update` (Ereignis `boxen`). Fehler wie bei `box/sync`, dazu `keine_version`. Fähigkeit `update`. |
| `tobibox/releases/list` | 3b | Liest die vorhandenen Pakete auf `releases/` (nur Name und Version). Rechte: alle. |
| `tobibox/eingang/track_anhaengen` | offen | Nachlieferung einzelner Tracks zu einer schon einsortierten Folge (11.3: in Version 1 nicht vorgesehen) |

**Erweiterungen v1.1, gültig seit dem 09.11. (AP 4.7).** Der Befund aus AP 3.2 (gegen den Code von AP 3.1
geprüft) nannte sechs Lücken. Alle sind **additiv** (Abschnitt 9, „Ohne Erhöhung“): Version 1 bleibt, es gibt keinen
neuen Wurzelnamen. Die Seite benutzt Neues nur, wenn `hello.faehigkeiten` es zusagt (Abschnitt 9, „Eingaben sind
strenger“); bei einem älteren Backend behilft sie sich wie bisher.

| Lücke (AP 3.2) | Jetzt gültig | Fähigkeit |
|---|---|---|
| Blockierten oder defekten Eingangseintrag entfernen | Befehl Nr. 33 `tobibox/eingang/entfernen` (`eintrag_id`, `bestaetigt`): Eintrag in den Papierkorb, Abschnitt 3.9 | `eingang_entfernen` |
| `papierkorb/restore` mit `serie_id`: Serie in der Seite wählen | **Kein neuer Befehl.** Das Eingabefeld `serie_id` gilt seit Nr. 11. Neu ist die Auswahl in der Seite: Für eine Folge, deren Serie es nicht mehr gibt (oder auf Wunsch „in andere Serie …“), wählt Tobias eine Serie aus `serien/list`; erst dann sendet die Seite `serie_id`. Auch wenn das Backend `serie_nicht_gefunden` meldet, fragt die Seite nach einer Serie und sendet noch einmal. | – (schon in Version 1) |
| Felder des Box-`status` genau benennen | **Kein neuer Befehl.** `boxen/list` gibt `status` unverändert weiter (Nr. 21); die Felder stehen in `mqtt-v1.md`, 3.3, und dieser Vertrag wiederholt sie nicht. Die Seite liest nur Felder aus 3.3; was fehlt, lässt sie weg oder zeigt „–“. | – |
| `zuordnung/list` mit Filter `uid` | optionale Eingabe `uid` bei Nr. 15 (genau eine Zuordnung oder keine) | `zuordnung_uid` |
| Lesebefehl für den Konfig-Stand | Befehl Nr. 34 `tobibox/konfig/get` mit `{"konfig": <Konfig-Stand>}` (alle), Abschnitt 3.10 | `konfig_lesen` |
| Ereignis „Upload fertig“ mit Dateiname und Prüfung | `fortschritt` mit `zustand="fertig"` trägt `datei` und `pruefung`, Abschnitt 4.7 | `upload_fertig_details` |

**Schon in Stufe 3a nötig:** Das Backend legt `leise_zeiten` (`zeitzone`
`Europe/Berlin`, `fenster` leer) und `gute_nacht` (`timer_min` 30, `ausblenden_s` 60,
die Vorschläge des Designs) in der Konfiguration an, weil `config.json` sie als Pflicht
verlangt, und schreibt sie bei jeder Änderung unverändert fort. Dasselbe gilt für die
optionalen Felder `ton_pegel`, `hinweis_pegel` und `lesezeichen_tage` (Entscheidung N, 09.11.):
`ton_pegel` und `hinweis_pegel` legt das Backend nicht an, **verliert sie aber nie** beim Schreiben
einer neuen Revision. **(09.11., Befund AP 3.1)** `lesezeichen_tage` legt es mit der Vorgabe 14 an
(Bereich 0 bis 365, `0` = nie), veröffentlicht es in jeder Liste, exportiert es und holt es mit
`konfig/aus_export` zurück; eine Bedienung gibt es vorerst nicht. **Lautheit (D6)** hat
keinen Befehl: Der Container läuft nach Zeitplan, ohne Auslöser aus HA (Design).
Sichtbar wird sie höchstens später als optionales Feld an der Folge.

## 11. Einsortieren nach Metadaten (Entscheidung M, 09.11.)

Tobias legt einen Ordner (zum Beispiel einen Hörbuch-Download) oder Dateien in den
**Eingang**. Die Integration liest die Tags der Audiodateien und sortiert **vollautomatisch**
in die Medienstruktur ein („wie bei Plex“), danach korrigiert Tobias auf der Seite. Die
Medienstruktur auf den Boxen bleibt unverändert (Serien-Ordner mit `serie.json`, Folgen
als Datei oder Folgen-Ordner, Entscheidung F); der Box-Code weiß davon nichts. Die
Regeln in diesem Abschnitt sind so festgelegt, dass jede Zeile als Test geschrieben werden
kann (`homeassistant/tests/test_eingang.py`, AP 3.1). Die Regeln gelten gleich für den
Eingang vom PC und für Uploads (Abschnitt 5).

### 11.1 Ort, Durchlauf, Ruhezeit

*   **Ort:** `tobibox/eingang/` auf dem NAS, **neben** `medien/`, `export/` und
    `releases/` (gleiche Freigabe, damit das Verschieben in `medien/` ein atomares
    Umbenennen ist). HA hat dort vollen Schreibzugriff (Entscheidung D); Tobias legt den
    Ordner an (AP 3.5). Fehlt er, antworten `eingang/list` und `eingang/sortieren` mit
    `medien_nicht_erreichbar`. Bleibt das Umbenennen aus technischen Gründen
    (anderes Dateisystem) aus, bleibt der Eintrag liegen, Hinweis
    `verschieben_fehlgeschlagen`; kopiert wird nie.
*   **Nicht gesynct:** Der Eingang liegt außerhalb des rsync-Moduls `medien` und wird von
    der Box **nie** geholt. Zusätzlich schließen NAS-Modul und Box die Namen
    `_upload`, `_papierkorb` und `eingang` im Sync aus (falls jemand einen davon in
    `medien/` anlegt; Design AP 3.4, AP 3.5). Die Prüfung der Integration ignoriert sie
    ebenfalls (Abschnitt 12).
*   **Eintrag:** Eine Datei oder ein Ordner auf der obersten Ebene von `eingang/`
    (Objekt in 3.9). Tiefer als 5 Ebenen im Eintrag wird nicht gelesen.
*   **Durchlauf:** Er läuft alle 10 min (Timer, nach der Prüfung der Freigabe), beim Öffnen
    der Seite, mit `eingang/sortieren` und 20 s nach dem letzten Upload (5.9). Immer nur
    **ein** Durchlauf zugleich; ein zweiter Aufruf meldet `laeuft_bereits`.
*   **Ruhezeit:** Ein Eintrag ist erst `bereit`, wenn (a) die neueste Änderungszeit aller
    Dateien darin mindestens 120 s (`EINGANG_RUHE_S`) zurückliegt **und** (b) Dateianzahl
    und Gesamtgröße beim vorigen Scan, der mindestens 30 s zurückliegt, gleich waren
    (b ist nötig, weil Kopierprogramme die alte Änderungszeit der Quelle übernehmen). Sonst
    `wartet`; solange ein Eintrag wartet, plant das Backend nach 60 s einen weiteren Durchlauf.
    `sofort=true` und Uploads übergehen die Ruhezeit.
*   **Ignoriert** werden Dateien, deren Name mit `.` beginnt (`._*` von macOS) und
    Dateien mit anderer Endung als der Liste aus `data-model.md`, Abschnitt 5 (Bilder,
    Texte). Sie werden gezählt (`ignoriert`).
*   **Reihenfolge der Einträge** im Durchlauf: `zuerst_gesehen` aufsteigend, bei Gleichheit
    die natürliche Sortierung des Namens (`data-model.md`, Abschnitt 5). Ihre laufende
    Nummer ist der **Eingangsindex** (0, 1, 2 …), der in 11.6 gebraucht wird.

### 11.2 Tags lesen

Die Tags kommen von `ffprobe` (gleicher gehärteter Aufruf wie 5.4): `format.tags` und die
Tags des ersten Audio-Stroms; ein Schlüssel in `format.tags` gilt vor dem Strom. Schlüssel
werden **ohne Unterscheidung von Groß-/Kleinschreibung** verglichen. Werte werden vor jeder
Auswertung **normiert**: Unicode NFC, Steuerzeichen entfernt, Leerraum gekürzt und auf ein
Leerzeichen zusammengefasst, auf 200 Zeichen gekürzt. Ein Wert ohne einen einzigen
Buchstaben oder eine Ziffer gilt als **leer**. Diese Schlüssel werden gelesen
(Aliase in Vorrangfolge, der erste nicht leere gilt):

| Feld | Tag-Schlüssel (Vorrang von links) | Auswertung |
|---|---|---|
| `album` | `album` | Text. Ein Zusatz am Ende der Form `(CD 2)`, `[Disc 1]`, `- CD 3`, auch `CD 2/4`, wird für Gruppenschlüssel und Anzeige entfernt (Teil `cd`, `disc`, `disk`; **nicht** `Teil`, denn „Teil 2“ ist oft eine eigene Folge). |
| `album_interpret` | `album_artist`, `albumartist`, `album artist` | Text. **Platzhalter** gelten als leer (Vergleich mit `norm`): `various artists`, `various`, `verschiedene`, `verschiedene interpreten`, `diverse`, `va`, `unknown`, `unbekannt`, `n/a`. |
| `interpret` | `artist`, `author`, `composer` | schwacher Rückgriff (11.5), gleiche Platzhalter wie oben |
| `serien_tag` | `series`, `serie`, `show`, `movement_name`, `mvnm`, `grouping`, `tit1`, `content_group` | Text. Bei m4b zum Beispiel die Atome für Serie/Satz, bei mp3 `TIT1`/`MVNM`. |
| `nummer_tag` | `series_part`, `series-part`, `seriespart`, `part`, `movement`, `mvin`, `episode_sort`, `episode_id` | die erste ganze Zahl am Anfang (`^\s*0*(\d{1,4})`); sonst leer |
| `titel` | `title` | Text |
| `track` | `track`, `tracknumber` | `3` oder `3/12` → 3 (die Zahl vor dem `/`); sonst leer |
| `disc` | `disc`, `discnumber`, `part_of_set` | `1` oder `1/2` → 1; sonst leer |
| `datum` | `date`, `originaldate`, `original_date`, `year` | `YYYY`, `YYYY-MM` oder `YYYY-MM-DD` (Jahr 1900–2100) → `YYYY-MM-DD`, fehlender Monat/Tag = `01`; sonst leer. **Nicht** `creation_time` (das ist der Zeitpunkt der Aufnahme der Datei). |

Die genauen Schlüsselnamen, die `ffprobe` je Container liefert (`mp3`, `m4a`/`m4b`,
`flac`, `ogg`), belegt AP 3.1 mit Beispieldateien von Tobias und ergänzt die Aliase in
dieser Tabelle (eine additive Änderung). **Vergleich** zweier Werte heißt immer
`norm(a) == norm(b)` mit `norm(x)`: Unicode NFKC, `casefold`, dann alle Zeichen entfernen,
die kein Buchstabe und keine Ziffer sind (`Die drei ???` → `diedrei`). Ergibt das leer,
gilt der gekürzte `casefold`-Wert.

**Folgen-Nummer aus einem Text** (Albumname, bei einer Einzeldatei auch der Titel): Es gilt
die erste passende Regel, innerhalb einer Regel der erste Treffer; Zahlen mit mehr als
4 Ziffern passen nie; führende Nullen zählen nicht (`007` → 7). Die Regeln (ohne
Unterscheidung von Groß-/Kleinschreibung):

| Nr. | Muster | Beispiel → Ergebnis |
|---|---|---|
| R1 | Stichwort `folge`, `teil`, `band`, `episode`, `ep`, `nr`, `nummer`, `vol`, `volume` (am Wortanfang), optional `.`, `:` oder `#`, dann die Zahl | `Der Rabe - Folge 12: Der Wald` → 12; `Nr. 3` → 3; `Teil 2 von 3` → 2 |
| R2 | Zahl am Textanfang, gefolgt von einem Trennzeichen `- – — : . _ )` und weiterem Text | `3 - Der Anfang` → 3; `007: Gold` → 7 |
| R3 | `#` und Zahl | `Abenteuer #5` → 5 |
| R4 | Zahl in runden Klammern am Textende | `Der Rabe (12)` → 12 |

`Das Jahr 1984` und `2000 Meilen` ergeben **keine** Nummer.

### 11.3 Gruppieren: Album = Folge

Die Einheit des Einlesens ist die **Datei**; die Einheit des Ergebnisses die **Gruppe**:
Eine Gruppe wird **eine Folge**. Besteht sie aus einer Datei, ist die Folge diese Datei;
besteht sie aus mehreren, ist die Folge ein **Folgen-Ordner mit Tracks** (Entscheidung F).

*   **Teil (14.11.):** In einem Ordner-Eintrag ist jeder **Unterordner der ersten Ebene** ein
    **Teil**; Dateien direkt im Eintrag gehören zum Teil „Eintrag selbst“. **Ausnahme:** Ein
    Unterordner, dessen Name nur eine CD- oder Disc-Angabe ist (Muster `cd`, `disc` oder `disk`,
    dann Zahl, Groß/klein egal: `CD1`, `CD 2`, `Disc 1`, `Disk 2`), ist kein eigener Teil, sondern
    gehört zum übergeordneten Teil (`Buch/CD1/` und `Buch/CD2/` sind der Teil `Buch`;
    `Eintrag/CD1/` gehört zum Eintrag selbst). Tiefere Unterordner gehören zum Teil ihrer ersten Ebene.
*   **Datei mit `album`, im Ordner-Eintrag:** Gruppe = (Eintrag, **Teil**, `norm(album)`). Dateien
    desselben Albums in `CD1/` und `CD2/` desselben Teils sind eine Gruppe; dasselbe Album in
    verschiedenen Teilen sind **verschiedene** Gruppen (Folgen).
*   **Datei mit `album`, lose in `eingang/`:** Gruppe = `norm(album)` über alle losen
    Dateien des Durchlaufs.
*   **Datei ohne `album`, im Ordner-Eintrag:** Alle solchen Dateien **eines Teils** bilden
    **eine** Gruppe (Kennzeichen `tags_fehlen`). Bei mehreren Dateien ist der Anzeigename der Name des
    **Teils** (Unterordner), bei Dateien des Teils „Eintrag selbst“ der Name des Eintrags (Folgen-Ordner). Ist es nur **eine** Datei, ist ihr Anzeigename der `titel`, sonst der
    Dateiname ohne Endung, nicht der Ordnername (09.11., Befund AP 3.1; Testfall T4).
*   **Datei ohne `album`, lose:** eine Gruppe je Datei (Kennzeichen `tags_fehlen`).
*   **Ein Ordner mit vielen Dateien ohne Tags** wird also eine Folge mit vielen Tracks
    (`bitte prüfen`). Aufteilen in einzelne Folgen geht in Version 1 durch **Unterordner** (je
    Unterordner eine Folge, 14.11.) oder durch Tags ergänzen und die Dateien erneut in den Eingang legen.
*   **Sammelordner (14.11.):** Ein Ordner mit einem Buch je Unterordner wird je Teil gruppiert; eine
    nicht abspielbare Datei hält nur das Buch zurück, in dem sie liegt (11.10).
*   **Nachlieferung:** Kommt später eine Datei zu einem Album, das schon einsortiert ist,
    wird sie eine **neue Folge** (Kennzeichen `folge_gleicher_name`); die vorhandene Folge
    wird nicht ergänzt (Version 1).

### 11.4 Tag → Ergebnis (Zusammenfassung)

| Ergebnis | Quelle, in Vorrangfolge | Kennzeichen, wenn die schwächere Quelle gilt |
|---|---|---|
| **Folge: Anzeigename** | 1. `album` (ohne CD-Zusatz); 2. bei einer einzelnen Datei der `titel`; 3. bei einer einzelnen Datei **der Dateiname ohne Endung** (nicht der Ordnername, auch wenn die Datei in einem Ordner-Eintrag liegt); bei einem Folgen-Ordner (mehrere Dateien ohne `album`) der **Name des Teils** (Unterordner der ersten Ebene, 11.3), bei Dateien direkt im Eintrag der **Name des Eintrags** (Ordner) (09.11., Befund AP 3.1; 14.11.) | `tags_fehlen` ab 2 |
| **Folge: Name auf der Platte** | Datei: Dateiname nach Abschnitt 12; Folgen-Ordner: Anzeigename nach Abschnitt 12 | `name_geaendert` bei Ersatzname |
| **Serie: Name** | 11.5 | `serie_aus_interpret`, `serie_aus_ordner` |
| **Folgen-Nummer** | 1. `nummer_tag`; 2. Regeln R1–R4 auf den Albumnamen; 3. bei einer Datei R1–R4 auf den Titel; 4. keine | – |
| **Datum** | frühester `datum` aller Dateien der Gruppe; sonst keines | – |
| **Reihenfolge der Folgen** | 11.6 | – |
| **Reihenfolge der Tracks** | 11.7 | `track_doppelt`, `track_teils_leer` |

### 11.5 Serie bestimmen und zusammenführen

Je Gruppe, in dieser Vorrangfolge (der erste Treffer gilt):

1.  **Vorgabe der Seite:** Kam die Datei per Upload mit `serie_id`, gilt diese Serie (auch
    die Überraschungs-Serie). Gibt es die Serie nicht mehr: weiter mit 2 und Kennzeichen
    `vorgabe_serie_fehlt`.
2.  **`serien_tag`** (Mehrheit in der Gruppe, 11.8).
3.  **`album_interpret`** (Mehrheit; Platzhalter zählen als leer).
4.  **`interpret`**, wenn alle Dateien der Gruppe denselben haben → Kennzeichen
    `serie_aus_interpret`.
5.  **Name des Ordners** → Kennzeichen `serie_aus_ordner`: liegt die Gruppe in einem Teil-Unterordner
    (11.3), der Name des **Teils**, sonst der Name des Eintrags (14.11.).
6.  Sonst (lose Datei ohne Tags) die Serie **`Einzelfolgen`** → Kennzeichen
    `serie_aus_ordner`.

Die Schreibweise des Namens ist die des ersten Treffers unter den Dateien der Mehrheit,
gekürzt auf 100 Zeichen.

**Zusammenführen:** Der **Serienschlüssel** eines Namens ist `norm(name)` (11.2). Alle
Gruppen eines Durchlaufs mit gleichem Schlüssel und alle vorhandenen Serien mit
`typ="normal"`, deren Anzeigename **oder** Ordnername denselben Schlüssel hat, sind
**dieselbe Serie**: Die Folgen werden dort einsortiert. Gibt es mehrere passende
vorhandene Serien, gilt die mit dem frühesten `angelegt_am` (Kennzeichen
`serie_mehrdeutig`). Gibt es keine, wird eine **neue** Serie angelegt (zufällige ID,
Ordnername nach Abschnitt 12, Anzeigename wie oben; ist die Quelle `interpret` oder der
Ordner, trägt die neue Serie selbst das Kennzeichen `pruefen`). Die Überraschungs-Serie
nimmt nie automatisch etwas auf (nur über die Vorgabe der Seite).

### 11.6 Reihenfolge der Folgen in der Serie

Jede Folge hat `nummer` (11.4), `datum` und ihren Eingangsindex (11.1). Der
**Sortierschlüssel** einer Folge:

```
mit Nummer:   (0, nummer, datum oder "9999-99-99", eingangsindex)
ohne Nummer:  (1, 0,      datum oder "9999-99-99", eingangsindex)
```

Die neuen Folgen einer Serie in einem Durchlauf werden nach diesem Schlüssel aufsteigend
geordnet: erst die mit Nummer (nach Nummer), dann die ohne (nach Datum, dann
Eingangsreihenfolge). Gleiche Nummern behalten die Reihenfolge von Datum und Eingangsindex
und tragen das Kennzeichen `nummer_doppelt`.

Eine **neue Serie** erhält diese Reihenfolge als `folgen`. In eine **vorhandene Serie**
wird jede neue Folge (in dieser Reihenfolge) **einzeln eingefügt**, ohne die vorhandene
Reihenfolge zu ändern (eine Reihenfolge, die Tobias von Hand gesetzt hat, bleibt):

*   Hat die neue Folge eine Nummer `n`, suche in der aktuellen Liste die Folgen mit
    bekannter Nummer (`folgen_info.nummer`). Gibt es eine mit Nummer **größer als `n`**,
    wird sie **vor der ersten** davon eingefügt; sonst **hinter der letzten mit Nummer
    ≤ `n`**; gibt es gar keine mit Nummer, **hinten**.
*   Hat sie keine Nummer, kommt sie **hinten** an.

Dieselbe Einfügeregel gilt für `folge/verschieben` und `serien/zusammenfuehren`.

### 11.7 Reihenfolge der Tracks und Dateinamen im Folgen-Ordner

Die Box ordnet die Tracks eines Folgen-Ordners nach der **natürlichen Sortierung der
Dateinamen** (`data-model.md`, Abschnitt 5). Das Backend baut deshalb die Namen so, dass
diese Sortierung die gewünschte Reihenfolge ergibt.

*   **Gewünschte Reihenfolge:** Sortiert nach (`disc`, `track`, natürliche Sortierung des
    relativen Pfads). Fehlt `disc`, kommt die CD-Nummer aus dem Albumnamen (Zusatz `CD 1`, `Disc 2` usw., 11.2), sonst gilt 1 (09.11., Befund AP 3.1). Dateien **mit** `track` kommen vor Dateien
    ohne (Kennzeichen `track_teils_leer`). Hat **keine** Datei `track`, gilt allein die
    natürliche Sortierung des relativen Pfads im Eintrag (Unterordner `CD1` vor `CD2`).
    Zwei Dateien mit gleichem (`disc`, `track`) bleiben beide, in Pfad-Reihenfolge
    (Kennzeichen `track_doppelt`).
*   **Namen:** Zuerst werden die Dateinamen nach Abschnitt 12 bereinigt (ohne Pfad). Ergibt
    die natürliche Sortierung dieser Namen **schon** die gewünschte Reihenfolge und sind
    die Namen (ohne Rücksicht auf Groß-/Kleinschreibung) eindeutig, **bleiben sie**.
    Sonst erhalten **alle** Tracks der Folge das Präfix `NNN ` (laufende Nummer ab 1,
    mindestens drei Stellen, bei mehr als 999 Tracks so viele wie nötig), z. B.
    `001 Kapitel 1.mp3`.
*   Eine Folge aus einer Datei wird nicht umbenannt (außer nach Abschnitt 12).

### 11.8 Widersprüche in einem Ordner

Die Tags innerhalb einer Gruppe stimmen oft nicht überein. Regel für jedes Feld
(`serien_tag`, `album_interpret`, `interpret`, `nummer_tag`, `datum`): Es zählen nur nicht
leere Werte; die **Mehrheit** nach `norm` gewinnt, bei Gleichstand der Wert der ersten Datei
in der gewünschten Track-Reihenfolge. Haben die nicht leeren Werte **mehr als einen**
Wert, kommt ein Kennzeichen.

| Widerspruch | Regel | Kennzeichen |
|---|---|---|
| Verschiedene `album` in einem Ordner-Eintrag | verschiedene Gruppen, also verschiedene Folgen | – |
| Gleiches `album`, verschiedene `serien_tag` (oder, ohne diese, verschiedene `album_interpret`) | **eine** Gruppe, die Mehrheit bestimmt die Serie | `serie_widerspruch` |
| Gleiches `album`, verschiedene `nummer_tag` | Mehrheit | `nummer_widerspruch` |
| Gleiches `album`, verschiedene `datum` | das früheste | – |
| Einige Dateien eines Ordners ohne `album`, andere mit | die ohne bilden je Teil eine eigene Gruppe (11.3) | `tags_fehlen` |
| Gleiches (`disc`, `track`) zweimal | beide bleiben (11.7) | `track_doppelt` |
| `track` nur bei einem Teil der Dateien | die mit `track` zuerst (11.7) | `track_teils_leer` |
| Zwei Gruppen im Durchlauf mit gleicher Serie und gleicher `nummer` | beide bleiben (11.6) | `nummer_doppelt` |

### 11.9 Fehlende Tags und „bitte prüfen“

Eine Folge ist **„bitte prüfen“**, sobald sie mindestens ein Kennzeichen trägt. Die
Kennzeichen (`pruefen_gruende`) und ihre Bedeutung:

| Code | Bedeutung |
|---|---|
| `tags_fehlen` | kein `album`: Name und Serie stammen aus Ordner- und Dateinamen |
| `serie_aus_interpret` | die Serie stammt nur aus `interpret` |
| `serie_aus_ordner` | die Serie stammt aus dem Ordnernamen oder ist `Einzelfolgen` |
| `serie_widerspruch` | verschiedene Serienangaben in einem Album (Mehrheit gilt) |
| `serie_mehrdeutig` | mehrere vorhandene Serien passen; die älteste wurde genommen |
| `nummer_widerspruch` | verschiedene Folgen-Nummern in einem Album |
| `nummer_doppelt` | die Nummer gibt es in der Serie schon |
| `track_doppelt`, `track_teils_leer` | siehe 11.7 |
| `name_geaendert` | der Name musste durch einen Ersatz (`Unbenannt`) oder durch starkes Kürzen ersetzt werden (Abschnitt 12) |
| `folge_gleicher_name` | die Serie hat schon eine Folge mit demselben Anzeigenamen |
| `teilweise_doppelt` | ein Teil der Dateien war schon vorhanden und wurde verworfen (11.10) |
| `vorgabe_serie_fehlt` | die vom Upload vorgegebene Serie gibt es nicht mehr |

Die Kennzeichen stehen in `serie.json` (`folgen_info.<name>.pruefen`, `pruefen_gruende`;
bei der Serie selbst `pruefen`, `pruefen_gruende`; `data-model.md`, Abschnitt 5), damit sie
den Neustart von HA überleben. Sie verschwinden mit `einsortierung/bestaetigen` und durch
die Korrekturen aus 3.9. **Fehlende Tags sind nie ein Fehler**: Die Datei wird trotzdem
einsortiert.

### 11.10 Blockiertes, Doppeltes, Reste

*   **Kopierschutz und defekte Dateien (Vorgabe 8):** Jede Datei wird vor dem Einsortieren
    nach D5 geprüft (`ffprobe` gehärtet wie 5.4; Codec `drms`; `ffprobe` scheitert;
    Probedekodierung von 1 s). Eine Datei mit `kopierschutz`, `nicht_lesbar` oder
    `probedekodierung_fehlgeschlagen` kommt **nicht in die Medien**, sie bleibt im
    Eingang mit Hinweis (Eingangs-Eintrag, `hinweise`). Fehlt `ffprobe`: Der ganze
    Durchlauf bleibt liegen (`ffprobe_fehlt`), denn ohne `ffprobe` gibt es keine Tags.
    **Eine Gruppe wird nur vollständig einsortiert:** Ist auch nur eine Datei einer Gruppe
    blockiert, bleibt die **ganze Gruppe** im Eingang (die gute Datei ist dann ohne
    Folge nutzlos); andere Gruppen desselben Eintrags werden einsortiert (Status
    `teilweise`). Ein Eintrag ohne eine einzige Audiodatei bleibt mit dem Hinweis
    `keine_audiodateien` liegen.
*   **Doppelte (Vorgabe 7):** Von jeder Datei wird die **SHA-256-Prüfsumme** des Inhalts
    gebildet (im Executor, in Blöcken). Sie wird verglichen mit (a) dem **Index** im
    HA-Speicher (Prüfsumme → Pfad der Datei in `medien/`; es zählt nur ein Eintrag,
    dessen Datei noch am Pfad liegt und dieselbe Größe hat; der Index nimmt alles auf, was
    das Einsortieren und der Upload nach `medien/` gebracht haben, und verliert die
    Einträge, deren Folge in den Papierkorb geht oder verschoben wird; er wird beim
    Wiederherstellen ergänzt; höchstens 20 000 Einträge), (b) den anderen Dateien des
    Durchlaufs, (c) einer gleichnamigen Datei im Ziel. Bei gleicher Prüfsumme gilt die
    Datei als **doppelt**: Sie kommt in den Papierkorb (`typ="eingang"`,
    `grund="doppelt"`, wiederherstellbar) und bekommt den Hinweis `doppelt` im Ergebnis.
    Dateien, die von außen direkt in `medien/` kamen, kennt der Index nicht; sie werden
    nur gefunden, wenn der Name gleich ist (c).
    Ist nur ein Teil einer Gruppe doppelt, werden die doppelten Dateien verworfen und der
    Rest als Folge einsortiert (Kennzeichen `teilweise_doppelt`); ist **alles** doppelt,
    entsteht keine Folge.
*   **Gleicher Name, anderer Inhalt (Vorgabe 7):** Gibt es im Ziel schon eine Datei oder
    einen Ordner mit dem Namen (ohne Rücksicht auf Groß-/Kleinschreibung und Unicode-Form),
    erhält die neue ` (2)`, ` (3)` … vor der Endung (Abschnitt 12).
*   **Reste:** Ist ein Eintrag fertig (nichts blockiert, nichts mehr zu sortieren), kommen
    seine ignorierten Dateien (Bilder, Texte) in den Papierkorb (`typ="eingang"`,
    `grund="eingang_rest"`) und leere Unterordner werden gelöscht; der Eintrag
    verschwindet aus dem Eingang. Er steht als `erledigt` im Protokoll.

### 11.11 Schreiben in die Medien (Reihenfolge, Abbruch)

Je Gruppe, unter den Sperren aus Abschnitt 1 (Eingang, dann Serie):

1.  **Berechnen** ohne Schreiben (Tags, Prüfsummen, Serie, Reihenfolge, Namen, Kennzeichen).
2.  **Serie anlegen**, wenn neu: Ordner, `serie.json` (`folgen` leer; atomar nach
    `data-model.md`, 1.2).
3.  **Dateien verschieben** (Umbenennen auf derselben Freigabe, nie kopieren): Eine
    Einzeldatei direkt in den Serien-Ordner (nach erneuter Namensprüfung unter der Sperre).
    Ein Folgen-Ordner wird zuerst vollständig unter `medien/_upload/<zufall>/` aufgebaut
    und dann **als ganzer Ordner** in den Serien-Ordner umbenannt. Die Box sieht so nie
    einen halben Ordner (und ohne Eintrag in `folgen` spielt sie ihn ohnehin nicht).
4.  **`serie.json` schreiben:** die Folge nach 11.6 in `folgen` einfügen, `folgen_info`
    ergänzen (`anzeige`, `nummer`, `datum`, `pruefen`, `pruefen_gruende`). Atomar.
5.  **Index, Protokoll und Ereignisse:** Prüfsummen in den Index, Eintrag ins Protokoll
    (HA-Speicher, die letzten 100), Ereignisse `neu_einsortiert` und `serien_geaendert`.

Bricht HA zwischen 3 und 4 ab, liegt die Datei im Serien-Ordner, steht aber nicht in
`folgen`; die nächste Prüfung der Freigabe (`medien/pruefen`) trägt sie **hinten** ein
(wie jede von außen gekommene Datei). Es geht nichts verloren; nur Nummer und Anzeigename
fehlen, und die Folge ist nicht „bitte prüfen“. Kein Schritt wird an die Boxen gemeldet;
sie holen die Folge mit dem nächsten Sync.

### 11.12 Beispiele als Testfälle

Jede Zeile ist ein Test in `test_eingang.py` (Tags sind mit `ffprobe`-Schlüsseln
geschrieben; „→“ ist das Ergebnis).

| Nr. | Eingang | Ergebnis |
|---|---|---|
| T1 | Ordner `Hörbuch X/` mit 12 mp3, alle `album="Hörbuch X"`, `album_artist="Autor A"`, `track=1..12` | Serie `Autor A` (neu, ohne `pruefen`), **eine** Folge `Hörbuch X` als Ordner mit 12 Tracks, Dateinamen unverändert |
| T2 | 5 mp3 in einem Ordner, jede mit eigenem `album="Der kleine Rabe - Folge N: …"` (N = 3, 1, 5, 2, 4 in Dateireihenfolge), `album_artist="Der kleine Rabe"` | Serie `Der kleine Rabe`, 5 Folgen in der Reihenfolge Nummer 1, 2, 3, 4, 5 (Nummer aus R1) |
| T3 | m4b mit `series="Die Känguru-Chroniken"`, `series-part="2"`, `album="Und überhaupt"`, `album_artist="Marc-Uwe Kling"` | Serie `Die Känguru-Chroniken` (der `serien_tag` schlägt den Interpreten), Folge `Und überhaupt`, Nummer 2 |
| T4 | Datei ohne Tags in `Märchen/` | Serie `Märchen`, Folge (Datei) mit Anzeigename = Dateiname ohne Endung (nicht der Ordnername; der gilt nur für Folgen-Ordner, 11.4); Kennzeichen `tags_fehlen`, `serie_aus_ordner`; Serie `pruefen` |
| T5 | lose Datei `x.mp3` ohne Tags | Serie `Einzelfolgen`; Kennzeichen wie T4 |
| T6 | Zwei Durchläufe nacheinander, `album_artist` = `Die drei ???` und `die drei ???` | **eine** Serie (gleicher Serienschlüssel `diedrei`) |
| T7 | Ordner, `album` gleich, `serien_tag` 3-mal `A`, 1-mal `B` | eine Gruppe, Serie `A`, Kennzeichen `serie_widerspruch` |
| T8 | 2 Dateien `a.mp3` (track 2), `b.mp3` (track 1), gleiches Album | Folgen-Ordner mit `001 b.mp3`, `002 a.mp3` (Reihenfolge ≠ natürliche Namensordnung → Präfix) |
| T9 | wie T8, aber `a.mp3` track 1 und `b.mp3` track 2 | Namen bleiben `a.mp3`, `b.mp3` |
| T10 | Album mit 3 Dateien, eine mit Codec `drms` | die **ganze Gruppe** bleibt im Eingang, Hinweis `kopierschutz` an der Datei; Eintrag `blockiert` (andere Gruppen im Eintrag werden einsortiert, Status `teilweise`) |
| T11 | dieselbe Datei (gleiche Prüfsumme) liegt schon als einsortierte Folge in `medien/` und kommt noch einmal in den Eingang | die neue Datei kommt in den Papierkorb (`grund="doppelt"`), keine neue Folge, Hinweis `doppelt` |
| T12 | `Folge 1.mp3` mit anderem Inhalt, im Ziel gibt es schon eine gleichnamige | neue Datei heißt `Folge 1 (2).mp3` |
| T13 | 3 Folgen ohne Nummern, `date` = 2001, 1999, 2000 | Reihenfolge 1999, 2000, 2001 |
| T14 | 3 Folgen ohne Nummer und ohne Datum, Eingangsindex 0, 1, 2 | Reihenfolge 0, 1, 2 |
| T15 | Serie hat Folgen mit Nummer 1, 2, 3 (und hinten eine ohne), neue Folge Nummer 4 | wird hinter 3 und **vor** der Folge ohne Nummer eingefügt; eine neue mit Nummer 2 kommt hinter die vorhandene 2 und trägt `nummer_doppelt` |
| T16 | `album_artist="Various Artists"` | gilt als leer; die Serie kommt aus `interpret` oder dem Ordner (Kennzeichen) |
| T17 | `album="Hörbuch X (CD 1)"` und `(CD 2)` | eine Gruppe, Anzeige `Hörbuch X` |
| T18 | Upload mit `serie_id` einer vorhandenen Serie | Serie = Vorgabe, auch gegen die Tags |
| T19 | Eintrag, dessen neueste Datei 30 s alt ist | Status `wartet`, nichts verschoben (mit `sofort=true`: einsortiert) |
| T20 | Dateiname `Folge 1: Der Rabe.mp3` | Zielname `Folge 1 - Der Rabe.mp3` (Abschnitt 12) |
| T21 | Ordner `Sammlung/` mit `Buch A/` (3 Dateien ohne Tags), `Buch B/` (2 Dateien, eine nicht abspielbar), `Buch C/CD1/` und `Buch C/CD2/` (gleiches `album`) | Serie `Buch A` (Ordner, 14.11.) mit **einer** Folge (3 Tracks); für Buch C eine Serie aus den Tags mit **einer** Folge aus CD1 und CD2; `Buch B` bleibt ganz im Eingang (Hinweis nennt die Datei); Eintrag `teilweise` |

## 12. Namen und reservierte Ordner

Diese Regeln gelten für **jeden** Datei- und Ordnernamen, den das Backend auf der
Freigabe anlegt (Upload, Einsortieren, `serie/create`, Verschieben, Suffixe). Namen, die
schon auf der Freigabe liegen, werden nicht umgeschrieben.

1.  **Unicode NFC.** Neue Namen sind NFC (macOS liefert NFD; SMB und QNAP vergleichen
    uneinheitlich).
2.  **Verbotene Zeichen** der SMB-Freigabe ersetzen, nicht ablehnen: `:` wird zu ` - `
    (`Folge 1: Der Rabe` → `Folge 1 - Der Rabe`; vorhandene Leerzeichen um den Doppelpunkt
    gehen darin auf), `/ \ * ? " < > |` werden zu `_`, Steuerzeichen (U+0000 bis U+001F,
    U+007F) entfallen.
3.  **Ränder:** Leerraum zu einem Leerzeichen zusammenfassen, am Anfang und Ende kürzen;
    **führende Punkte und führende `_` entfallen** (kein Dotfile, kein reservierter Name);
    **Punkte und Leerzeichen am Ende entfallen** (Windows).
4.  **Gerätenamen** (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`, ohne
    Rücksicht auf Groß-/Kleinschreibung, mit oder ohne Endung) erhalten ein `_` davor;
    `.` und `..` werden zu `_`. **Ausnahme Serien-Ordner (09.11., Befund AP 3.1):** Ein führendes
    `_` ergäbe einen reservierten Ordner (siehe unten). Darum bekommt ein Gerätename als Serien-Ordner
    das `_` **hinten**: `CON` wird `CON_`, nicht `_CON`. **(09.11., AP 4.7, Fehlerbehebung)** Dasselbe Prinzip gilt für
    `.` und `..`: Als Serien-Ordner ergeben sie **keinen Namen** (Regel 6; vorher fälschlich `_ordner`, ein reservierter
    Ordner), als Datei oder Folgen-Ordner bleibt es bei `_`. Ein Gerätename gilt für den Teil **vor dem ersten
    Punkt** (`CON.txt` wird als Datei `_CON.txt`, als Serien-Ordner `CON_.txt`), und auch `COM¹` bis `COM³` und
    `LPT¹` bis `LPT³` sind Gerätenamen.
5.  **Länge:** höchstens 255 Bytes (UTF-8) **und** 255 UTF-16-Einheiten, die kürzere Grenze
    gilt, abzüglich Platz für ` (99)`; gekürzt wird an einer **Zeichengrenze** (nie mitten
    in einem UTF-8-Zeichen), die Endung bleibt erhalten. Ein Kürzen um mehr als nur das
    Suffix trägt das Kennzeichen `name_geaendert`.
6.  **Leer** nach allem: beim Upload und bei `serie/create` `name_ungueltig`; beim
    Einsortieren der Name `Unbenannt` (Kennzeichen `name_geaendert`).
7.  **Namensgleichheit** wird ohne Rücksicht auf Groß-/Kleinschreibung und nach NFC geprüft
    (auf der SMB-Freigabe sind `Folge.MP3` und `folge.mp3` dieselbe Datei), **unter der
    Sperre**, und bei Treffer hängt das Backend ` (2)`, ` (3)` … vor die Endung (bei
    Ordnern ans Ende). Ab ` (99)` gibt es `medien_schreibfehler`.
8.  **Anzeigenamen** (Serie 1–100, Folge 1–200, Tobie 1–60 Zeichen) sind frei bis auf
    Steuerzeichen (entfernt); `:` bleibt erlaubt, denn sie sind kein Dateiname.

**Reservierte Ordner in `medien/`:** Ordner, deren Name mit `_` beginnt (`_papierkorb`,
`_upload`), und der Name `eingang` (ohne Rücksicht auf Groß-/Kleinschreibung) sind **keine
Serien**. Die Prüfung der Integration legt für sie keine `serie.json` an und meldet
`reservierter_ordner`; die Namensregeln 3 und 7 verhindern, dass das Backend selbst einen
solchen Serien-Ordner anlegt (`serie/create` mit dem Namen „eingang“ ergibt den Ordner
`eingang (2)`). Der Sync der Box lässt sie aus (11.1).

## 13. Zustand der Konfiguration: leerer Speicher, Export, Boxen mit neuerem Stand

Dieser Abschnitt sichert gegen das stille Ausrollen einer **leeren** Liste und gegen eine
Sicherung mit **alter Revision** ab (W-01, W-02, W-06). Hintergrund: Die Boxen nehmen eine
Liste mit neuer Listen-ID immer an, auch eine leere (`mqtt-v1.md`, 5.2); eine Liste mit
gleicher Listen-ID und niedrigerer Revision lehnen sie ab.

### 13.1 Die drei Zustände (`konfig.zustand`)

| Zustand | Bedeutung | Die Integration |
|---|---|---|
| `ok` | Normalbetrieb | verteilt, was Befehle ändern |
| `leer_neu` | Der HA-Speicher ist leer (neu aufgesetzt oder verloren), obwohl es schon einmal eine Konfiguration gab | **veröffentlicht nichts**, legt keine Listen-ID an, bis Tobias entscheidet |
| `export_neuer` | Der Export auf dem NAS ist neuer als der HA-Speicher (HA wurde aus einer Sicherung zurückgespielt) | veröffentlicht nichts Neues, bis Tobias entscheidet |

### 13.2 Erkennung beim Start

Die Integration prüft **beim Start** (nach Verbindung zum Broker, mit bis zu 15 s Wartezeit
auf die dauerhaften `status`-Nachrichten der Boxen):

1.  **Speicher leer** (kein Eintrag `.storage/tobibox` oder ohne Konfiguration):
    *   Gibt es **keine** Exportdatei **und** meldet **keine** Box eine `konfig.liste_id`
        im dauerhaften `status`: **Erststart**. Die Integration legt eine neue Liste an
        (Revision 1, neue Listen-ID), veröffentlicht sie, `zustand="ok"`.
    *   Sonst (es gab schon eine Konfiguration): `zustand="leer_neu"`, **keine** Listen-ID,
        **keine** Veröffentlichung.
2.  **Speicher vorhanden:** Der Export ist **neuer**, wenn er lesbar und gültig ist und
    (a) seine `liste_id` gleich der im Speicher ist und seine `revision` **höher**, oder
    (b) seine `liste_id` anders ist und sein `exportiert_am` **nach** dem
    `export_geschrieben_am` liegt, den dieser Speicher zuletzt selbst geschrieben hat.
    Dann `zustand="export_neuer"`. Sonst `ok`.

### 13.3 Verhalten außerhalb von `ok`

*   Alle Befehle, die die Konfiguration ändern (Spalte „MQTT“ mit `tobibox/config`,
    außer den beiden Auswegen), antworten `konfig_nicht_bereit`; ebenso `lernmodus/start`.
*   Lesen, Medien, Eingang, Neue Tobies, Boxen, Sync gehen weiter. Bestätigungen `neu` und
    `bekannt` auf `…/ack` gehen weiter.
*   Die Seite zeigt eine Warnung, die den Unterschied erklärt, und bietet **nur** die
    Auswege an:
    *   **Aus dem Export holen** (`konfig/aus_export`): übernimmt den Export mit neuer
        Listen-ID und Revision 1.
    *   **Stand von HA behalten / leer beginnen** (`liste/neu_ausrollen`): erzeugt eine
        neue Listen-ID aus dem Stand in HA (bei `leer_neu`: eine **leere** Liste; die Seite
        sagt vorher, dass alle Tobies ihre Zuordnung verlieren).

### 13.4 Box mit neuerem Stand (`voraus`)

Ist die `liste_id` einer Box (aus `status.konfig`) gleich der von HA und ihre `revision`
**höher**, ist `konfig_stand="voraus"` (3.7). Meldet eine Box `liste_abgelehnt` mit
`revision_zu_niedrig`, gilt dasselbe. In beiden Fällen sendet das Backend das Ereignis
`konfig` `abweichung` (4.6). **Die Integration erhöht die Revision nie von selbst** (das
würde gegen die Boxen laufen und könnte einen Stand überschreiben, den nur die Box hat). Der
Ausweg ist derselbe wie oben: `liste/neu_ausrollen` oder `konfig/aus_export`.

### 13.5 Export (W-06)

*   Der Export `export/config.json` (Schema von `config.json` plus `exportiert_am`,
    `data-model.md`, Abschnitt 1.6) wird **nach dem Veröffentlichen** im Hintergrund
    geschrieben (Abschnitt 1) und enthält die Tobie-Namen.
*   Schlägt er fehl (NAS im Standby, Netz), wiederholt das Backend nach 10 s, 60 s, 5 min,
    dann alle 15 min, bis er gelingt oder eine neuere Revision ihn ersetzt. Solange gilt
    `konfig.export_ok=false`; das Ereignis `konfig` `export_fehler` meldet es,
    `export_ok` meldet das Nachholen, und die Seite zeigt eine Warnung (das Sicherungsnetz
    fehlt!).
*   Der Befehl, der die Änderung auslöste, bleibt davon unberührt.

### 13.6 Wiederverbinden

Kehrt der Broker zurück, veröffentlicht das Backend die **aktuelle** Konfiguration noch
einmal (retained), wenn eine Veröffentlichung offen ist (`veroeffentlicht=false`). Die
Revisionsregel der Boxen macht das unschädlich. Offene `ack` des Lernmodus folgen
danach (6.2, Schritt 4).

### 13.7 Tests

`homeassistant/tests/test_restore.py` (AP 3.1) prüft: (a) **leerer Speicher mit
vorhandenem Export und Box-Status** → `leer_neu`, nichts veröffentlicht, Befehle
`konfig_nicht_bereit`; (b) **Erststart** (kein Export, kein Status) → neue Liste,
veröffentlicht; (c) Zurückspielen mit höherer Export-Revision → `export_neuer`;
(d) `konfig/aus_export` → neue Listen-ID, Revision 1, Namen übernommen, `zustand="ok"`;
(e) `voraus` und `abweichung`; (f) Export schlägt fehl → Befehl gelingt, `export_ok=false`,
Wiederholung; (g) „Liste neu ausrollen“ nach Wiederherstellung mit alter Listen-ID.

## 14. Erweiterungen der HA-Oberfläche, Stufe A (12.11.)

Dieser Abschnitt legt die Regeln fest, auf die sich die Befehle 37 bis 46 (3.12) und die geänderten Stellen in 2, 3, 5, 7 und 8 stützen. Grundlage: `docs/designs/ha-oberflaeche.md`, Abschnitte 5, 10, 11 (V-1 bis V-9); Entscheidungen: `docs/egm/ha-ui/resolve.md`. **Alles ist additiv, mit den Ausnahmen, die der Änderungseintrag am Anfang dieses Vertrags nennt.** Stufe A läuft in drei Teilen mit je eigener Abnahme: **A-1** Alltag (Bibliothek, Tobies, Hochladen, Abends, Rechte, Cover), **A-2** Reinhören mit Weiterhören, **A-3** Hörkopien und Kapitel. Der Vertrag gilt für alle drei; ein Teil schaltet seine Fähigkeiten erst, wenn er gebaut ist.

### 14.1 Fähigkeiten (Regel)

Eine Fähigkeit gibt es **nur** (1) für etwas, das von der Umgebung abhängt (`ffmpeg`), oder (2) für **neue Eingabefelder und Eingabewerte**, die ein älteres Backend (neue JavaScript-Dateien werden sofort ausgeliefert, Python erst nach dem Neustart von HA) streng ablehnen würde (Abschnitt 9, „Eingaben sind strenger“). Reine neue Ausgabefelder brauchen keine: die Seite zeigt sie, wenn sie da sind. Neue Werte in `hello.faehigkeiten` (ans Ende der Liste):

| Fähigkeit | Teil | Bedeutung |
|---|---|---|
| `cover` | A-1 | Foto-Upload, Cover-Ansicht, Befehl 44; das **Lesen aus Tags** nur, wenn `ffmpeg` da ist (Skalieren macht Pillow) |
| `bibliothek` | A-1 | `serien/list` mit `art`, `text`, `auch_folgen`, `filter` (**einschließlich der Werte `sammlung` und `einzeln`**), `sortierung`, `limit`, `offset`; Befehle 37 und 38; `erwartet_revision` bei `einstellungen/set`; `text` und `neu` bei `zuordnung/list` |
| `einsortier_wunsch` | A-1 (Befehl 43: A-3) | Upload-Felder `ziel`, `art`, `name`, `gruppe_anzahl`; Befehl 43. Ohne sie zeigt die Seite das alte, einfache Hochladen ohne Wahl |
| `reinhoeren` | A-2 | Audio-Ansicht, Befehle 39 bis 42; Sortierung `angehoert`. Ohne sie zeigt die Seite keinen Reinhören-Knopf |
| `hoerkopie` | A-3 | hängt von `ffmpeg` ab: Audio-Ansicht liefert Kopien, Zustand in `audio/bereit`, Befehl 45. Ohne sie bleibt es bei der Prüfung mit `canPlayType` |
| `konfig_staende` | A-1 | optionale Eingabe `stand` bei `konfig/export_lesen` und `konfig/aus_export` (2.4) |
| `warteschlange` | A0-Q (13.11.) | Befehle 47 bis 49, Ereignisthema `warteschlange` in `subscribe.themen`, Feld `hello.grenzen.warteschlange_max`, Abgleich beim Auflegen (3.13) |
| `zuordnung_rueckgaengig` | A0-Q (13.11.) | optionale Eingabe `als_neu` bei `zuordnung/remove` (3.5). Eigene Fähigkeit, weil „Rückgängig“ (X20d) vor der Warteschlange gebaut werden kann |

**Entfallen** (in Rev. 5 des Designs gestrichen): `kapitel` (das Feld `kapitel` ist ein Ausgabefeld; fehlt es, zeigt die Seite keine Liste), `box_anzeigenamen` und `rechte_stufen` (Feld da bzw. Seite und Backend liegen im selben Paket). Fehlt eine Fähigkeit, die die Seite braucht, zeigt sie **eine** Antwort („Die Seite ist veraltet. Bitte lade sie neu.“). Eine **alte Seite** im Zwischenspeicher kennt die neuen Befehle nicht, schickt sie nicht und blendet nach `darf_schreiben` aus: harmlos. Stufe B (`gehoert`, `gehoert_reinhoeren`) und Stufe C (`playlists`): geplant, siehe Design Abschnitt 12 und 13; sie gehören **nicht** zu diesem Vertragsstand.

### 14.2 Bibliothek: Art, Einzeltitel, Suche, Felder (V-2, V-8)

**Serie-Kurzform bekommt** (alle Ausgabefelder; Fähigkeit nicht nötig):

| Feld | Typ | Bedeutung |
|---|---|---|
| `art` | `hoerspiel`, `hoerbuch`, `musik`, `geschichte` | Art des Eintrags; fehlt sie in `serie.json`, gilt `hoerspiel` |
| `art_quelle` | `tags`, `geraten`, `manuell` | woher `art` kommt; `manuell` wird nie überschrieben |
| `einzeln` | bool | Einzeltitel (14.4); fehlt = `false` |
| `kapitel_anzahl` | int | Summe der Kapitel aller Folgen (A-3); 0 oder fehlt = keine Liste |
| `dauer_s` | Zahl oder `null` | Summe der bekannten Folgendauern (A-2); `null`, solange unbekannt |
| `cover_stand` | string (8 Zeichen `[0-9a-f]`) oder `null` | Fingerabdruck der angezeigten Bilddatei; `null` = kein Cover |
| `cover_quelle` | `eigen`, `auto` oder `null` | |
| `hoerstelle` | object | nur wenn der Anfragende angefangen hat: `anteil` (Zahl 0 bis 1), `rest_s`, `zeit`, `folge`; **nur seine eigene** (A-2) |

Schon vorhanden und unverändert benutzt: `anzahl_folgen`, `anzahl_tobies` (zählt `serie` **und** `folge`), `angelegt_am`. Bei einem Einzeltitel ist `anzahl_folgen` 1. Ereignisse (`medien`, `snapshot`) tragen kein Cover, nur Antworten auf Befehle. Die Adresse des Covers ist fest (`/api/tobibox/cover/<serie_id>`, 14.3), es gibt kein signiertes `cover_url`.

**`serien/list` bekommt optionale Eingaben** (Fähigkeit `bibliothek`):

| Eingabe | Typ | Bedeutung |
|---|---|---|
| `art` | siehe oben | nur Einträge dieser Art |
| `text` | string, 2–100 Zeichen | sucht im Namen des Eintrags (normalisiert); mit `auch_folgen=true` auch in Folgentiteln |
| `auch_folgen` | bool | Vorgabe `false` |
| `filter` | array aus `ohne_tobie`, `neu`, `pruefen`, `sammlung`, `einzeln` | `sammlung` = nur Einträge, die kein Einzeltitel sind; `einzeln` = nur Einzeltitel; mehrere Werte gelten als „und“ |
| `sortierung` | `name` (Vorgabe), `neu`, `angehoert` | `angehoert` = zuletzt angehört vom Anfragenden, nur mit Fähigkeit `reinhoeren` |
| `limit` | int 1–200 | |
| `offset` | int ≥ 0 | |

Die Ausgabe bekommt `gesamt` (nach Filter) und `weitere` (bool). **Fehlt `limit`, gilt das bisherige Verhalten: alle** (dazu `weitere`); so bleibt die alte Seite gültig. Das 64-KiB-Limit einer Nachricht (Abschnitt 8) bleibt gewahrt, weil die neue Seite blättert. Die Integration hält Eintrags- und Folgennamen (normalisiert) im Speicher (Aufbau beim Start, Aktualisierung bei `serien_geaendert`); Ziel: 600 Einträge, 2 000 Folgen, Suche unter 200 ms.

**`zuordnung/list`** bekommt die optionalen Eingaben `text` (string, 2–100 Zeichen: Tobie-Name oder Ziel) und `neu` (bool; `true` = zuletzt angelegt zuerst) sowie in `zuordnungen[]` das optionale Feld `angelegt_am` (Zeitstempel; die Box ignoriert es, `data-model.md`, 1.4).

**Art beim Einsortieren vorschlagen** (Ergänzung zu 11.4): Genre-Tag mit „Hörbuch“/„Audiobook“/„Spoken“ oder Endung `.m4b` → `hoerbuch`; Genre „Hörspiel“/„Audio Drama“/„Radio Play“ → `hoerspiel`; Musikgenre (Pop, Kinderlieder, Children’s Music, Klassik, Schlaflied …) oder viele kurze Tracks (Mittel unter 8 Minuten) mit Album-Interpret → `musik`; Märchen/Geschichten oder Einzeldatei unter 30 Minuten ohne Album → `geschichte`; sonst `hoerspiel` mit `art_quelle="geraten"` und dem Grund `art_geraten` in `pruefen_gruende`. Die genauen Regeln werden vor Abschluss von A3 an je fünf echten Dateien je Art geprüft (Entscheidung Tobias/Empfehlung, Frage 4); das Ergebnis ändert nur diese Liste. Ein von Hand gesetztes `art` (`manuell`) wird **nie** überschrieben.

**Einzeltitel** sind eine **normale Serie** mit genau einer Folge und `einzeln: true` (eigene ID, Ordner, `serie.json`, Cover, Papierkorb, Umbenennen, Befehl 38). Neue Folgen kommen nicht hinein: `ergaenzen` (14.4) antwortet `wunsch_ungueltig`, `folge/verschieben` mit einem Einzeltitel als Ziel `ziel_ungueltig`; `serien/zusammenfuehren` darf ihn als Quelle, nicht als Ziel benutzen. Ein Tobie auf einen Einzeltitel zeigt auf die **Folge** (`ziel.typ="folge"`), nicht auf die Serie.

**Folge-Objekt von `serie/get` bekommt** (Ausgabefelder): `dauer_s` (Zahl oder fehlt), `spuren_s` (bei Ordner-Folgen: Liste der Track-Längen), `kapitel` (Liste aus `titel`, `start_s` und bei Ordner-Folgen `track` (0-basiert), nur wenn mindestens zwei, Regeln 14.7), `hoerstelle` (`position_s`, `fertig`; nur des Anfragenden, nur wenn angefangen) und `hoerkopie` (`original`, `nicht_angelegt`, `wartet`, `fertig`, `fehler`; bei `fehler` zusätzlich `grund`). **`stand`** der Serie rechnet künftig **nur** über `name`, `folgen` und die von Menschen gesetzten Felder von `folgen_info` (`anzeige`, `nummer`, `datum`, `pruefen`); Werte aus dem Store `tobibox.medieninfo` und Hintergrundläufe ändern ihn nie (Abschnitt 3, Serie-Kurzform).

### 14.3 Cover (V-1, Fähigkeit `cover`)

*   **`GET /api/tobibox/cover/<serie_id>?groesse=klein|gross`:** `image/jpeg`; `klein` 192 px, `gross` 512 px; `ETag` = `cover_stand` **in Anführungszeichen** (K3, 12.11.; der Server nimmt `If-None-Match` mit und ohne Anführungszeichen sowie mit `W/` an); `Cache-Control: private, max-age=86400`. Recht: lesen (Anmeldung per `Authorization`-Kopf; die Seite lädt mit `hass.fetchWithAuth` und hält das Bild als `blob:`). 404 `cover_nicht_gefunden`.
*   **`POST /api/tobibox/cover/<serie_id>`:** Rumpf `image/jpeg`, höchstens `COVER_UPLOAD_MAX_BYTES`, Quadrat bis auf `COVER_QUADRAT_TOLERANZ`, höchstens `COVER_KANTE_MAX_PX` je Seite. **Reihenfolge im Backend:** (1) der Rumpf wird **in Blöcken gelesen und gezählt** (die Grenze gilt auch ohne `Content-Length`), (2) Typ aus den Kopfbytes, (3) **Maße und Pixelzahl aus dem Kopf lesen, bevor ein Pixel dekodiert wird**, (4) erst dann dekodieren, auf `COVER_GROSS_PX` und `COVER_KLEIN_PX` herunterrechnen und als `cover-eigen.jpg` speichern; das Original wird nie gespeichert. Dieselbe **eine** Funktion `cover_pruefen_und_skalieren` hat **zwei Modi** (K2, 12.11.): **`streng`** (Foto-Upload, wie oben: JPEG, quadratisch bis `COVER_QUADRAT_TOLERANZ`, höchstens `COVER_KANTE_MAX_PX`) und **`nachsichtig`** (Tag-Bilder und mitgelieferte Dateien, unten): nur die Pixelobergrenze `COVER_NACHSICHT_PIXEL_MAX` (16 000 000) vor dem Dekodieren prüfen, dann verkleinern, EXIF-Drehung anwenden, mittig quadratisch zuschneiden. Recht: alltag; Menge `COVER_JE_STUNDE` je Benutzer. Fehler: `cover_ungueltig` (400), `datei_zu_gross` (413), `serie_nicht_gefunden` (404), `zu_viele_aenderungen` (429).
*   **`DELETE /api/tobibox/cover/<serie_id>?quelle=eigen`:** zurück zum automatischen Cover. Recht: alltag. **Ohne eigenes Cover ist DELETE kein Fehler** (K3): Antwort 200, nichts ändert sich. **Antwort von POST und DELETE** (K3): `{v, serie_id, cover_stand, cover_quelle}`.
*   **Automatisches Cover:** Beim Einsortieren liest die Integration das eingebettete Bild (ID3 `APIC`, MP4 `covr`, FLAC `PICTURE`) der ersten Folge, die eines hat, nur mit `ffmpeg`. **Vorrang** hat ein mitgeliefertes `cover.jpg`, `folder.jpg` oder `cover.png` im Eingangs-Ordner: die Integration **kopiert** es (durch `cover_pruefen_und_skalieren` im Modus `nachsichtig`) als `cover.jpg` in den Serien-Ordner; die mitgelieferte Datei im Eingang folgt danach der **bisherigen Regel** (Reste gehen in den Papierkorb, 11.10 bleibt unverändert). Je Eintrag eine **Marke „schon gesucht“** (`cover_suche`: `tags`, `datei` oder `keine`, mit Zeit) im Store `tobibox.medieninfo` (`data-model.md`, 5a). Nachholen für bestehende Einträge nur (a) einmal im Hintergrund nach dem Start der Integration, (b) für Einträge ohne Marke, (c) mit Zeitgrenze `COVER_SUCHE_ZEITGRENZE_S` je Datei und Abbruch bei `medien_nicht_erreichbar`. Neue Folgen in einem Eintrag mit Marke `keine` lösen genau eine neue Suche aus. **Kein Dauer-Scan:** `medien/pruefen` startet keine Cover-Suche; die Seite ruft es höchstens alle `PRUEF_INTERVALL_S` und nur sichtbar. Fehlt `ffmpeg`: die Fähigkeit bleibt (Foto-Upload geht), nur das Lesen aus Tags entfällt, ohne Fehlermeldung. Die Tag-Suche probiert höchstens `COVER_SUCHE_DATEIEN_MAX` (5) Dateien je Eintrag (K3, 12.11.).
*   `manifest.json` bekommt `"requirements": ["Pillow"]`.
*   **Auf den Boxen:** `cover*.jpg`, `cover*.png` und `folder.jpg` werden **nicht synchronisiert** (`data-model.md`, Abschnitt 5; Änderung in `box/src/tobibox/sync.py`).

### 14.4 Hochladen mit Wunsch (V-7, Fähigkeit `einsortier_wunsch`)

**Upload** (`POST /api/tobibox/upload`, 5.1) bekommt **optionale** Felder, wie die vorhandenen als Text im Multipart, **vor** dem Teil `datei`: `ziel` (`auto` Vorgabe, `neu`, `ergaenzen`, `einzeln`), `art` (`hoerspiel`, `hoerbuch`, `musik`, `geschichte`), `name` (1 bis 100 Zeichen, nach den Namensregeln aus Abschnitt 12 bereinigt; **bis 400 Bytes lesbar**, bei Überlauf `wunsch_ungueltig`) und **`gruppe_anzahl`** (ganze Zahl 2 bis `GRUPPE_ANZAHL_MAX`: die Zahl der Dateien dieser `gruppe`). Die vorhandenen Felder `upload_id`, `serie_id` und `gruppe` bleiben. Fehlt `ziel`, gilt `auto`: **genau das heutige Verhalten** (11.3 bis 11.5), dazu der Art-Vorschlag (14.2). Eine alte Seite sendet nie etwas davon. (`ziel=playlist` gehört zu Stufe C: geplant, siehe Design Abschnitt 13.)

| `ziel` | Pflicht | Ergebnis |
|---|---|---|
| `auto` | – | wie heute, dazu der Art-Vorschlag |
| `neu` | `gruppe`, `gruppe_anzahl` (bei mehr als einer Datei), `art`, `name` | **eine neue Serie** `name`; wird **nie** in eine vorhandene gleichen Namens zusammengeführt (gibt es den Namen, heißt sie „… (2)“, Hinweis `serie_name_doppelt`). Die **Gruppierung folgt der Art**, nicht den Tags: `hoerbuch` = **alle** Dateien eine Folge (Folgen-Ordner, die Tracks sind die Kapitel; bei einer Datei die Datei selbst); `hoerspiel`, `musik`, `geschichte` = **jede Datei eine Folge** (auch wenn alle dasselbe Album nennen). Reihenfolge nach 11.6 und 11.7. `art_quelle="manuell"` |
| `ergaenzen` | `serie_id`, `gruppe`, `gruppe_anzahl` (bei mehr als einer Datei) | jede Datei eine **neue Folge** der vorhandenen Serie (Einfügeregel 11.6), nie ein Folgen-Ordner. Die Serie darf kein Einzeltitel sein (`wunsch_ungueltig`) |
| `einzeln` | `art` (Vorgabe `musik`) | **jede Datei eine neue Serie mit genau einer Folge und `einzeln: true`**; `name` = Titel dieser einen Datei (sonst Tag `title`, sonst Dateiname). Mehrere Dateien: je Datei ein eigener Upload mit eigenem `name`, ohne gemeinsame `gruppe` |

*   **Eine Gruppe bleibt zusammen:** Hat ein Wunsch `gruppe_anzahl` N, **wartet der Eingang, bis N Dateien der Gruppe da sind**, oder `GRUPPE_RUHE_MAX_S` Ruhe vergangen sind (dann Status `teilweise` mit dem Hinweis `gruppe_unvollstaendig`; einsortiert wird, was da ist). Die Sammelzeit `UPLOAD_SAMMELZEIT_S` (5.9) gilt für Uploads ohne `gruppe_anzahl` unverändert. Ohne `gruppe_anzahl` ist `neu` oder `ergaenzen` mit mehreren Dateien `wunsch_ungueltig`. Der Wunsch wird je Gruppe einmal gespeichert (im persistenten `vorgaben` der Integration).
*   **Fehler:** `wunsch_ungueltig` (400) bei fehlenden Pflichtfeldern oder unpassender Mischung; `serie_nicht_gefunden` wie bisher. Die Prüfung der Datei (Format, Kopierschutz, Probedekodierung) bleibt unverändert (5.4).
*   **Anzeige:** `eingang/list`-Einträge (3.9) tragen zusätzlich `quelle` (`upload` oder `nas`, **fest**, die Integration weiß es), `wunsch` (`{ziel, art}` oder `null`) und `pruefen` (bool: mindestens ein Eintrag in `ergebnis` hat `pruefen=true`); das Ereignis `eingang` trägt `wunsch` im Eintrag mit.
*   **Hinweis `gruppe_unvollstaendig`** (Eingangs-Eintrag, kein Fehlercode der HTTP-Antwort) und `serie_name_doppelt` kommen zu den Hinweis-Codes in 3 (Serie-Kurzform) bzw. 3.9.

### 14.5 Reinhören: Audio-Ansicht und Zugriff (V-6, Fähigkeit `reinhoeren`)

*   **`GET /api/tobibox/audio/{serie_id}/{folge_id}`** (optional `?track=<n>`, 0-basiert): `requires_auth = True`, `cors_allowed = False`, Recht lesen, Anmeldung **oder gültige Signatur** (`?authSig=…`), nur GET (und HEAD). `folge_id` ist der **Name der Folge** wie in `serie.json` `folgen`; die Seite bildet **jedes Pfadsegment mit `encodeURIComponent`**.
*   **Pfad-Sicherheit (IDs statt Pfade):** (1) `serie_id` muss die ID einer **bekannten** Serie sein; (2) `folge_id` muss **genau** einem Eintrag in `serie.folgen` entsprechen (Vergleich der ganzen Zeichenkette, keine Pfadbildung aus der Eingabe); (3) `track` ist eine Zahl, die Datei kommt aus der **eigenen sortierten Trackliste**; (4) **zwei getrennte Zweige:** (a) **Original**: Wurzel ist der aufgelöste Medien-Pfad, der fertige Pfad wird **aufgelöst** (`resolve()`) und muss darunter liegen (`is_relative_to`), sonst 404; (b) **Hörkopie**: Wurzel ist der aufgelöste Ordner `hoerkopien/` (außerhalb von `medien/`), der Pfad entsteht **nur** aus `serie_id` und `kennung`, beide vom Backend erzeugt, dann `resolve()` und `is_relative_to(hoerkopien)`; eine Kopie ist über keine andere `serie_id` erreichbar; (5) nur Dateien, keine Ordner; Endung aus `ENDUNGEN`; (6) Systemordner (`_papierkorb`, `_upload`, `eingang`, `export`, `releases`, `hoerkopien`, alles mit `.`, `@`, `#`, `$` am Anfang) sind nie eine Serie, also nie erreichbar. Kein `..`, keine absoluten Pfade, keine Pfade in Fehlertexten.
*   **Antwort:** eine Unterklasse von `aiohttp.web.FileResponse` (Range, ETag, Last-Modified), `Content-Type` aus einer **eigenen Tabelle** (mp3 `audio/mpeg`, m4a und m4b `audio/mp4`, aac `audio/aac`, flac `audio/flac`, ogg und opus `audio/ogg`, wav `audio/wav`; Hörkopie `audio/mp4`), `X-Content-Type-Options: nosniff`, `Cache-Control: private, max-age=3600`, **kein** `Content-Disposition: attachment`, Antwortkopf `X-Tobibox-Quelle: original` oder `kopie`. **Range ist Pflicht** (206, `Content-Range`, `Accept-Ranges: bytes`, 416 bei Unmöglichem; nur ein Bereich je Anfrage).
*   **Fehler:** 401 ohne gültige Anmeldung (macht HA), 404 `folge_nicht_gefunden` (auch für unbekannte Serie), 429 `zu_viele_streams`, 503 `medien_nicht_erreichbar`; 503 `hoerkopie_wartet` mit `Retry-After: 60` nur als Rückfall für Aufrufer, die `audio/bereit` nicht benutzt haben. `<audio>` meldet 401, 429, 503 und 404 **gleich** (`MediaError` Code 4); darum fragt die Seite **vor jedem Start und nach jedem Fehler** per `audio/bereit`, nie mit einem alten Link per `fetch` (ein 401 wäre ein „fehlgeschlagener Login“ in HA, mit Meldung „Login attempt failed“ und bei gesetzter Schwelle IP-Bann).
*   **Zähler:** höchstens `AUDIO_VERBINDUNGEN_JE_BENUTZER` **offene** Audio-Verbindungen je Benutzer, darüber 429 `zu_viele_streams`. Der Zähler zählt in `prepare()` der `FileResponse`-Unterklasse hoch und gibt im `finally` frei (ein Zähler um den Rückgabewert des Handlers zählt zu früh herunter).
*   **Signierter Pfad:** `audio/bereit` bildet ihn mit `async_sign_path` (wie HAs `auth/sign_path`) für die Anmeldung der Verbindung, Gültigkeit `AUDIO_LINK_GUELTIG_S` (24 Stunden, wie HA für Medien). Die Signatur bindet Pfad **und** Abfrage-Teile (`?track=2` ist mitsigniert, je Track neu signieren) und die Anmeldung (Refresh-Token): Wird die Sitzung des Kontos beendet, sind alle Links tot. Die Seite erneuert den Link bei jedem Start einer Folge und nach 20 Stunden; sie fragt nur die Folge, die sie gleich spielt (und die nächste im Voraus). Wer die Adresse hat, kann **diese eine Datei** bis zum Ablauf abrufen (kein Rechtezuwachs, keine Liste).
*   **Formate:** `ENDUNGEN`. Browser spielen MP3 und AAC (M4A/M4B) überall; OGG, Opus, ALAC, FLAC und WAV bekommen eine Hörkopie (14.8). Ohne `ffmpeg` bleibt für diese Formate der Rückfalltext „Das kann dieser Browser nicht abspielen. Auf der Box spielt es trotzdem.“

### 14.6 Hörstelle (V-6)

*   **Speicher:** HA-`Store` `tobibox.hoerstellen` (Version 1, `.storage/`), gesammelt gespeichert mit `async_delay_save` (`HOERSTELLE_SPEICHER_VERZOEGERUNG_S`): im Speicher sofort, auf der Platte gesammelt. Form: `{ "<user_id>": { "<serie_id>": { "zeit": <ISO>, "folge": "<Name>", "folgen": { "<Name>": { "p": <s>, "d": <s>, "t": <ISO>, "fertig": false, "track": 0 } } } } }`. Je Benutzer höchstens `HOERSTELLE_MAX_SERIEN` Serien und `HOERSTELLE_MAX_FOLGEN` Folgen je Serie (darüber fallen die ältesten weg). Beim Start fallen Einträge unbekannter Benutzer, gelöschter Serien und nicht mehr vorhandener Folgen weg.
*   **Kein Zugriff auf fremde Hörstellen** (2.1). Hörstelle und Box-Stelle (`resume.json`) sind getrennt: das Reinhören verändert die Stelle der Box nie und umgekehrt.
*   **Wann die Seite speichert:** höchstens alle 10 Sekunden während der Wiedergabe, sofort bei Pause, Sprung, Wechsel der Folge, Ende, Schließen der Seite. Zwei Geräte: „zuletzt gespeichert gewinnt“ je Folge.

### 14.7 Medieninfo: Dauer, Kapitel, Codecs (A-2, A-3)

*   **Quelle:** ein `ffprobe`-Durchgang je Datei (mit `-show_chapters`) liefert `dauer_s`, bei Ordner-Folgen `spuren_s`, `kapitel` und den Codec **je Track** (`codecs`). Beim Einsortieren gespeichert; für den Bestand einmal im Hintergrund nachgeholt (nur Folgen ohne `dauer_s`, eine Datei nach der anderen, feste Zeitgrenze `MEDIENINFO_ZEITGRENZE_S` je Datei, Abbruch bei `medien_nicht_erreichbar`, **kein Scan beim Öffnen der Seite**).
*   **Ablage:** Store `tobibox.medieninfo` (`data-model.md`, 5a), **nicht** `serie.json` (ein Hintergrundlauf darf `stand` nicht ändern und keine Datei auf dem NAS schreiben).
*   **Deckel und Plausibilität:** Die Integration speichert **keine Dauer über `DAUER_DECKEL_S`** (eine gültige FLAC-Datei mit digitaler Stille kann bei 500 MiB rund 940 Stunden haben); `hoerkopie` wird dann `fehler` mit Grund `zu_lang`. Zeitleiste und Gesamtdauer zeigen „–“.
*   **Kapitel, Quellen in dieser Reihenfolge:** (1) eingebettete Kapitel (`ffprobe -show_chapters`, M4B-Kapitelspur, MP3 ID3v2 `CHAP`); (2) bei einer Ordner-Folge ist jeder **Track** ein Kapitel (Titel aus dem Tag `title`, sonst Dateiname ohne Endung und ohne führende Nummer; Start = Summe der vorigen `spuren_s`); (3) sonst keine. Eingebettete Kapitel gewinnen vor den Tracks. Sortiert nach `start_s`; doppelte Startzeiten und Rückwärtssprünge fallen weg; höchstens `KAPITEL_MAX` je Folge, Titel höchstens `KAPITEL_TITEL_MAX` Zeichen; Liste nur bei mindestens zwei. Die Hörstelle bleibt, wie sie ist (`track`, `position_s`). Die Box bekommt Kapitel nie.

### 14.8 Hörkopie (V-9, Fähigkeit `hoerkopie`)

*   **Zweck:** Reinhören geht für jede Datei des Bestands, auf jedem Gerät, mit Springen, ohne Umwandeln beim Abspielen. Die **Box bekommt immer das Original**.
*   **Bedarf, je Track** (`braucht_hoerkopie(codec)`, eine Stelle im Code): `mp3` und `aac` → Original; `vorbis`, `opus`, `alac`, `flac`, `pcm_*` und alles Unbekannte → Kopie. Die Folge ist `fertig`, wenn alle Tracks fertig sind, die eine Kopie brauchen.
*   **Zeitpunkt (Entscheidung Tobias, Runde 10):** (a) **neu Einsortiertes sofort**, im Hintergrund, die Meldung „fertig“ wartet nicht darauf; (b) **der Bestand erst beim ersten Reinhören** (`audio/bereit` stellt die Datei in die Warteschlange und antwortet `wird_vorbereitet`); (c) Vorgezogenes geht an die Spitze, je Benutzer höchstens `HOERKOPIE_VORZIEHEN_JE_BENUTZER` Datei zugleich. Es gibt **keinen** Hintergrund-Lauf über den Bestand für Hörkopien. Zustand im Bestand bis dahin: `nicht_angelegt`.
*   **Erzeugen:** `ffmpeg -nostdin -v error -protocol_whitelist file -f <Format der Endung> -i file:<Pfad> -map 0:a:0 -vn -ac 2 -map_metadata -1 -t <Dauer + HOERKOPIE_T_ZUGABE_S> -fs <Grenze> -c:a aac -b:a 96k -movflags +faststart -f mp4 file:<Ziel>.part`, danach umbenennen. Liste von Argumenten, nie Shell, `RLIMIT_AS`; Programm: Erstwahl `get_ffmpeg_manager(hass).binary`, wenn die Integration `ffmpeg` geladen ist, sonst `shutil.which("ffmpeg")`. Bei Ordner-Folgen eine Kopie je Track.
*   **Ort:** auf der NAS-Freigabe im Ordner **`hoerkopien/<serie_id>/<kennung>.m4a`**, **neben** `medien/` (wie `export/`, `eingang/`, `releases/`), nicht in `medien/` und nicht in HAs Konfigurationsordner. Er liegt außerhalb des rsync-Moduls `medien`; die Box holt ihn nie, `sync.py` braucht dafür keine Ausnahme. `kennung` = die ersten 16 Zeichen von `sha1(folge|track|größe|Änderungszeit)`; ändert sich das Original, entsteht eine neue Kopie; verwaiste Kopien räumt ein Hintergrundlauf weg. `*.part` wird beim Start gelöscht.
*   **Harte Grenzen** (gelten für `ffmpeg` und für `ffprobe`; Namen und Werte in 14.10, **vorläufig bis zur Messung A0b**): Dauerdeckel; **feste** Zeitgrenze je Datei (nicht aus der Dauer im Dateikopf gerechnet); Ausgabe höchstens Dauer + Zugabe (`-t`); Ausgabe höchstens Dauer × 12 KB/s × 1,2 (`-fs`); Plausibilität Größe zu Dauer (Faktor über der Grenze: keine Kopie, Grund `unplausibel`); Schlange mit Höchstzahl und Höchstgröße (darüber `hoerkopie_warteschlange_voll`; der Zähler steht in „Technik“); Kontingent für `hoerkopien/` (darüber `kein_speicher`, nichts wird gelöscht); eine Datei zugleich, mit `nice`.
*   **Fehlerfall:** (1) `ffmpeg` fehlt: keine Fähigkeit, keine Kopien, kein Fehler. (2) Kodieren schlägt fehl (kaputte Datei, `zu_lang`, `zeitgrenze`, `unplausibel`, `kein_speicher`, NAS weg): `hoerkopie.zustand = "fehler"` mit `grund`; **ein Versuch je Datei und Start der Integration**, danach erst wieder auf `hoerkopie/neu_erzeugen`. NAS weg pausiert die Schlange. (3) Die Box ist nie betroffen. Papierkorb und Umbenennen berühren die Kopien nicht; Verschieben und Zusammenführen ändern die `serie_id`, die Kopie wird beim nächsten Lauf unter der neuen ID wiedergefunden oder neu gemacht; endgültiges Löschen räumt der Hintergrundlauf auf.

### 14.9 Anzeigenamen der Boxen (V-3)

Die Optionen der Integration bekommen **ein Textfeld** „Namen der Boxen“ (`box1=Box 1, box2=Box 2`; gleiche Prüfung wie bei den Box-Namen, höchstens 40 Zeichen je Name). `boxen/list` trägt je Box `anzeige` (nie `null`: Name aus den Optionen, sonst `anzeigename` der Discovery, sonst `box`); `hello` trägt `box_anzeigen` (object: Box-Name → Anzeige). Im Repo steht kein echter Name.

### 14.10 Konstanten und Grenzen (Stufe A)

Namen sind die der Konstanten im Code (`const.py`). **„vorläufig“** heißt: die Zahl ist ein Vorgabewert, den die Messung A0b (Testpanel auf Tobias’ HA, `ffmpeg`-Zeiten, Upload über Nabu Casa) bestätigt oder ändert; der Name bleibt.

| Konstante | Wert | Stand |
|---|---|---|
| `UPLOAD_MAX_MIB_VORGABE` | 2048 (2 GiB je Datei; bestehende Einträge mit 500 werden beim Update angehoben) | beschlossen (Runde 10) |
| `UPLOAD_RESERVE_BYTES` | 2 GiB; laufende Zwischendateien (angekündigte Bytes) werden vom freien Platz abgezogen | beschlossen |
| `UPLOAD_BYTES_JE_STUNDE` | 16 GiB je Benutzer | beschlossen |
| `AENDERUNGEN_JE_MINUTE` | 30 | beschlossen |
| `PAPIERKORB_AKTIONEN_JE_10_MIN` | 20 | beschlossen |
| `PAPIERKORB_MELDUNG_AB` | mehr als 3 Einträge in einer Stunde, oder ein Eintrag mit Tobies | beschlossen |
| `KONFIG_STAENDE_ANZAHL` | 10 | beschlossen |
| `EINSORTIERUNG_NEU_ALTER_MAX_S` | 86400 | beschlossen |
| `GRUPPE_ANZAHL_MAX` | 200 | beschlossen |
| `GRUPPE_RUHE_MAX_S` | 1800 | beschlossen |
| `COVER_UPLOAD_MAX_BYTES` | 3 MiB | beschlossen |
| `COVER_KANTE_MAX_PX` | 2048 | beschlossen |
| `COVER_QUADRAT_TOLERANZ` | 2 % | beschlossen |
| `COVER_GROSS_PX`, `COVER_KLEIN_PX` | 512, 192 | beschlossen |
| `COVER_JE_STUNDE` | 20 je Benutzer | beschlossen |
| `COVER_SUCHE_ZEITGRENZE_S` | 20 | beschlossen |
| `COVER_NACHSICHT_PIXEL_MAX` | 16 000 000 Pixel, vor dem Dekodieren (Modus `nachsichtig`, K2) | beschlossen (12.11.) |
| `COVER_SUCHE_DATEIEN_MAX` | 5 Dateien je Eintrag bei der Tag-Suche (K3) | beschlossen (12.11.) |
| `AUDIO_VERBINDUNGEN_JE_BENUTZER` | 6 | beschlossen (Review G5) |
| `AUDIO_BEREIT_JE_MINUTE` | 6 je Benutzer | beschlossen |
| `AUDIO_LINK_GUELTIG_S` | 86400 (24 Stunden) | beschlossen (Runde 10) |
| `HOERSTELLE_SCHREIBEN_JE_MINUTE` | 30 je Benutzer | beschlossen |
| `HOERSTELLE_SPEICHER_VERZOEGERUNG_S` | 60 | beschlossen |
| `HOERSTELLE_MAX_SERIEN`, `HOERSTELLE_MAX_FOLGEN` | 2000, 100 | beschlossen |
| `HOERSTELLE_DAUER_UNBEKANNT_MAX_S` | 86400 | beschlossen |
| `MEDIENINFO_ZEITGRENZE_S` | 20 je Datei (zusätzlich `FFPROBE_ZEITLIMIT_S` 30) | beschlossen |
| `KAPITEL_MAX`, `KAPITEL_TITEL_MAX` | 500, 120 Zeichen | beschlossen |
| `HOERKOPIE_KBIT` | 96 | beschlossen (Runde 8, Nr. 26) |
| `DAUER_DECKEL_S` | 172800 (48 Stunden) | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_ZEITGRENZE_S` | 5400 (90 Minuten je Datei, fest) | **beschlossen (K5, 12.11.: Messung A0b, 40× Echtzeit auf dem QNAP)** |
| `HOERKOPIE_T_ZUGABE_S` | 5 (zu `-t`) | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_FS_FAKTOR` | 12 KB/s × 1,2 (zu `-fs`) | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_PLAUSIBEL_FAKTOR` | 50 (Bytes je Sekunde gegen das übliche Maß) | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_SCHLANGE_DATEIEN`, `HOERKOPIE_SCHLANGE_BYTES` | 20 Dateien, 50 GB Quelle | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_KONTINGENT_BYTES` | 100 GB | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_VORZIEHEN_JE_BENUTZER` | 1 | **vorläufig, nach Messung A0b** |
| `HOERKOPIE_PARALLEL` | 1 | **vorläufig, nach Messung A0b** |
| `WARTESCHLANGE_MAX` | 5 Vormerkungen zugleich, über alle Boxen (3.13) | beschlossen (Design 5.13) |
| `WARTESCHLANGE_AENDERUNGEN_JE_MINUTE` | 30 je Benutzer, für `warteschlange/set` und `warteschlange/abbrechen` zusammen (2.4) | Vorschlag A0-Q, gleicher Wert wie `AENDERUNGEN_JE_MINUTE`; ein Höchstalter gibt es bewusst nicht (3.13, Regel 5) |
| Wartezeit-Schätzung in `audio/bereit.warte_s` | 15 bis 30 mal Echtzeit | **vorläufig, nach Messung A0b** |

`hello.grenzen` bekommt die Felder `audio_verbindungen_je_benutzer`, `hoerkopie_kbit`, `hoerkopie_dauer_max_s` und (13.11.) `warteschlange_max` (nur wenn die jeweilige Fähigkeit zugesagt ist) und `upload_max_bytes` mit dem neuen Wert.

### 14.11 Stufe B und C

*   **Stufe B** (Reiter „Gehört“, Favoriten, Technik-Verlauf, Reinhör-Daten): geplant, siehe Design Abschnitt 12. Noch nicht Teil dieses Vertrags.
*   **Stufe C** (eigene Playlists): geplant, siehe Design Abschnitt 13. Noch nicht Teil dieses Vertrags.

## Festlegungen in diesem Vertrag (Stand 09.11.)

Das Design lässt diese Einzelheiten offen. Entschieden wurde die einfachste
stimmige Lösung. Die Punkte 1 bis 14 stammen aus dem Entwurf vom 09.11. (vormittags) und
gelten mit den Änderungen aus der Überarbeitung; die Punkte 15 bis 24 sind neu; 25 bis 27 kamen mit Entscheidung N
und AP 4.7 dazu. **Alles
geht mit der Freigabe an Tobias**; die Vorgaben der Projektleitung (unten) gelten, bis er
widerspricht.

1.  **Rechte:** Lesen für jeden angemeldeten Nutzer, Schreiben nur Administratoren
    (2.1), abgeleitet aus Entscheidung D; die Seite nur für Administratoren
    (`require_admin=True`). **Ersetzt am 12.11.:** drei Stufen `lesen`, `alltag`, `admin` (2.1, 2.4); die Seite
    bleibt Administratoren vorbehalten, bis Teil A-1 abgenommen ist.
2.  **Ein Abo mit Themen** (`tobibox/subscribe`) statt eines Abos je Thema; Snapshots
    enthalten nur Zähler, nie Listen.
3.  **`anfrage_id`** für Befehle ohne natürliche Idempotenz (2.2); Speicherdauer
    10 min, 100 Stück, nur Erfolge.
4.  **`stand`** (Fingerabdruck) gegen gleichzeitige Änderungen von außen (drei
    Schreiber, Risiko im Design); die Seite muss ihn senden, wo die Reihenfolge, das
    Löschen oder das Verschieben von einem alten Bild der Seite ausgehen kann. Für
    Zuordnungen entsprechend `erwartet_ziel`.
5.  **Zuordnung vor Medien:** Eine Zuordnung darf auf eine Serie zeigen, die noch auf
    keiner Box ist (Design, `data-model.md`, Abschnitt 2), muss aber auf der Freigabe
    existieren.
6.  **Löschen einer zugeordneten Folge oder Serie** lässt die Zuordnung stehen und
    verlangt vorher eine Rückfrage mit Anzahl und Namen der Tobies.
7.  **Rückfrage-Frist** beim Überschreiben: `rueckfrage_bis` = das spätere von `frist_bis`
    (180 s) und Meldung + 60 s; HA-Benachrichtigung bei geschlossener Seite.
8.  **Rückfrage als Ereignis plus Antwortbefehl** statt eines Feldes in `lernmodus/start`.
9.  **Zwischendatei** für Uploads in `medien/_upload/` (gleiche Freigabe, gleiches
    Dateisystem), damit die Box nie halbe Dateien sieht.
10. **Kopierschutz = bleibt im Eingang mit Warnung, nicht in den Medien** (Vorgabe 8;
    ersetzt die Fassung „aufnehmen mit Warnung“ für alles, was durch den Eingang kommt).
11. **`medien/pruefen` und `eingang/sortieren` laufen im Hintergrund** und melden das Ende als
    Ereignis, damit der Befehl in 10 s antwortet.
12. **Fortschritt des Sendens misst der Browser;** Ereignisse gibt es nur für die
    Prüfung danach, an alle Abos des Nutzers.
13. **Neue-Tobies-Liste im HA-Speicher,** nicht in `tobibox/config` und ohne Revision.
14. **Papierkorb: wiederherstellen hinten in `folgen`;** die alte Position wird nicht
    gemerkt.
15. **Entscheidung M:** Eingang `tobibox/eingang/`, Einsortieren nach Tags, Korrektur auf der
    Seite (Abschnitt 11).
16. **Eingang neben `medien/`,** nicht darin: Das Umbenennen ist atomar, und der Sync sieht
    ihn nie; zusätzlich schließen NAS-Modul und Box die Namen aus.
17. **Upload geht in den Eingang;** die Seite kann die Serie als Vorgabe mitgeben
    (`serie_id`) und zusammengehörige Dateien mit `gruppe` bündeln (Auslegung der
    Projektleitung: Hochladen „in eine Serie“ bleibt möglich, durchläuft aber dieselbe
    Einsortierung).
18. **Eine Gruppe wird nur vollständig einsortiert** (11.10): Eine blockierte Datei hält die
    ganze Folge zurück. Seit 14.11. ist die Gruppe in einem Sammelordner ein **Teil** (Unterordner,
    11.3): Es bleibt nur das Buch mit der kaputten Datei liegen.
19. **Zeiger bei Verschieben und Zusammenführen:** Die Zuordnungen der Folgen-Tobies werden
    umgeschrieben, ihre Zeiger auf den Boxen beginnen von vorn (offener Punkt 3).
20. **Lernmodus, Ziel schon vorhanden:** `ack abgelehnt` statt `zugeordnet`, damit die Box
    ohne 10 s Stille das (identische) bestehende Ziel spielt; Tobias sieht „Der Tobie hat
    dieses Ziel schon.“ (6.2, Schritt 3).
21. **`ack` erst nach PUBACK** der Konfiguration; ohne PUBACK kein `ack` (W-07).
22. **Leerer Speicher veröffentlicht nichts** (Abschnitt 13); Erststart ist davon
    ausgenommen (kein Export, kein Box-Status).
23. **Export nach dem Veröffentlichen** mit Wiederholung und sichtbarem Fehler (W-06).
24. **Namen werden bereinigt statt abgelehnt** (Abschnitt 12); die Namensgleichheit prüft
    ohne Rücksicht auf Groß-/Kleinschreibung und NFC, unter der Sperre.
25. **Entscheidung N: Feld `lesezeichen_tage` reserviert** (Abschnitt 10, `data-model.md` Abschnitt 2).
    Das Backend legt es mit der Vorgabe 14 an (Bereich 0 bis 365, `0` = nie), veröffentlicht, exportiert
    es und holt es mit `konfig/aus_export` zurück (09.11., Befund AP 3.1). **(09.11., AP 4.7)** Die Seitenbedienung
    gibt es jetzt: `einstellungen/get` und `einstellungen/set` (Nr. 35 und 36). Version 1 bleibt.
26. **Erweiterungen v1.1 (09.11., AP 4.7):** `eingang/entfernen`, Filter `uid`, `konfig/get`, `datei` und
    `pruefung` im Ereignis „Upload fertig“ und die Serienauswahl bei `papierkorb/restore` gelten (Abschnitt 10). Die
    Seite nutzt sie nur, wenn `hello.faehigkeiten` sie zusagt. Version 1 bleibt, kein neuer Wurzelname.
27. **Einstellungen (09.11., AP 4.7):** Die Seite setzt Leise-Zeiten und Gute Nacht als **ganze Objekte**, den
    Ablauf der Lesezeichen als Zahl. HA prüft mit **derselben Prüfung wie die Box** (Abschnitt 3.11, 36); ungültig
    heißt: ganze Änderung abgelehnt, `einstellung_ungueltig` mit Pfad. Eine Änderung ist eine Änderung der
    Konfiguration (Revision + 1, `tobibox/config`). `hinweis_pegel` liest die Seite nicht und ändert sie nicht.

## Vorgaben der Projektleitung (09.11.)

Diese Entscheidungen zu den früheren „Offenen Punkten“ hat die Projektleitung getroffen
und in den Vertrag übernommen. **Tobias kann widersprechen.** Die Nummern sind die der
früheren Liste.

| Nr. | Punkt | Entscheidung | Wo im Vertrag |
|---|---|---|---|
| 1 | Seite für Nicht-Administratoren | nur Administratoren, `require_admin=True`; **seit 12.11.: bis zur Abnahme von Teil A-1, danach für alle HA-Benutzer** | 2.1 |
| 2 | „Bestätigen“ bei Neue Tobies | heißt zuordnen; das `ack` geht automatisch an die Box | 3.4 |
| 3 | „Umbenennen“ | nur **Anzeigenamen** von Serie und Folge (aus den Tags vorbelegt); Dateinamen bleiben, Zeiger gehen nie verloren | Nr. 6, 25 |
| 4 | Serie löschen | über den Papierkorb, mit Rückfrage; neuer Befehl `serie/delete` | Nr. 24 |
| 5 | Löschen mit Zuordnung | Rückfrage mit Anzahl und Namen der Tobies, danach Papierkorb; die Zuordnung bleibt, die Box spielt bis dahin die Überraschung | Nr. 8, 24, 6.3 |
| 6 | Größte Datei beim Upload | zunächst 500 MiB, einstellbar; die Abnahme misst am Handy über Nabu Casa. **Seit 12.11.: 2 GiB** (Entscheidung Tobias, Runde 10) | 5.1, 8 |
| 7 | Gleicher Dateiname | gleicher Inhalt (Prüfsumme): erkannt und verworfen mit Hinweis; gleicher Name, anderer Inhalt: automatisches Suffix | 11.10, 5.3 |
| 8 | Kopierschutz, defekt | bleibt im Eingang mit Warnung, nicht in den Medien | 5.4, 11.10 |
| 9 | Folgen-Ordner von der Seite | durch Entscheidung M erledigt (Tags bilden Folgen-Ordner, auch beim Upload) | 11.3 |
| 10 | Namen für Tobies | optionales Feld `name` je Zuordnung; die Box ignoriert es | Nr. 16, `data-model.md` |
| 11 | Rückfrage-Frist | 180 s; ohne offene Seite eine HA-Benachrichtigung (`persistent_notification`) | 6.2 |
| 12 | Zweiter Lernmodus | `lernmodus_laeuft`, erst abbrechen | Nr. 18 |
| 13 | Überraschungs-Serie | von der Seite anlegbar, wenn keine existiert; als Ziel einer Zuordnung verboten (`ziel_ungueltig`) | Nr. 3, 5, 16 |
| 14 | `_upload/`, `_papierkorb/` aus dem Sync | ausgenommen, dazu `eingang/`; vermerkt bei AP 3.4/3.5 im Design | 11.1, 12 |
| 15 | Papierkorb-Metadaten | Ordner `_papierkorb/<id>/` mit `meta.json`, in `data-model.md` | 3.3 |
| 16 | `limit`/`offset` | schon in Version 1 | Nr. 15 |
| 17 | Box-Meldungen | die letzten 20 je Box im HA-Speicher (überleben einen Neustart) | Nr. 21 |
| 18 | Leise-Zeiten | bleiben in Stufe 4 (AP 4.7); seit dem 09.11. (AP 4.7) gültig: `einstellungen/get` und `set` | 3.11 |
| 19 | HA-Version | **2026.11.x**; die genaue Patch-Version nennt Tobias beim Start von AP 3.1. Dazu Mosquitto-Add-on 7.1.3 und QNAP TS-464eU-8G (Celeron N5095, amd64) | 8, Plan Rev. 3.14 |
| 20 | Nabu Casa | wie 6: Abnahme am Handy mit 20, 150 und 500 MiB; **seit 12.11. zusätzlich 2 GiB** | 8 |

## Prüfung gegen die Home-Assistant-API

Geprüft am 09.11.2026 gegen den Quelltext von `home-assistant/core` (Zweig `dev`) und
aiohttp `master` (Goldfisch-Report, Abschnitt „Zu den Prüffragen“), soweit angegeben.
Alles andere stammt aus Wissen und ist in AP 3.1 gegen die feste HA-Version (2026.11.x)
zu belegen.

| Aussage | Stand |
|---|---|
| `websocket_api.websocket_command(schema)` setzt Schema und Befehlsnamen (`schema["type"]`); `extra` des Schemas lehnt Unbekanntes ab | geprüft (Quelltext). In `dev` heißt die Schema-Bibliothek in den Modulen `probatio`; das Verhalten ist das von `voluptuous` (Namensunterschied hängt an der HA-Version). Der Vertrag benutzt nur Typen (`str`, `int`, `bool`, Listen, Bereiche). |
| `websocket_api.async_response` führt den Handler als Hintergrundaufgabe aus; Pflicht für alles mit `await` | geprüft |
| `websocket_api.require_admin`: Nutzer muss `is_admin` sein, sonst `unauthorized` | geprüft. Reihenfolge der Dekoratoren wie in HA-Core: `@require_admin`, `@websocket_command(...)`, `@async_response` |
| `connection.send_result`, `send_error(msg_id, code, message)`, `send_event`, `send_message`; `websocket_api.event_message(id, event)` | geprüft |
| Abos: `connection.subscriptions[msg["id"]] = unsub`; das Beenden macht HAs `unsubscribe_events` (mit `subscription`); beim Trennen der Verbindung ruft HA alle `unsub` auf | geprüft (`subscriptions`, `async_handle_close`); `unsubscribe_events` aus Wissen |
| Fehlerobjekt hat nur `code` und `message` (plus Übersetzungsschlüssel) | geprüft |
| Eingebaute Fehlercodes `invalid_format`, `unauthorized`, `not_found`, `unknown_command`, `unknown_error`, `home_assistant_error` | geprüft (`const.py`) |
| `HomeAssistantView`: `requires_auth = True` und `cors_allowed = False` als Vorgabe; nicht angemeldete Anfrage → 401 vor dem Handler; Attribut `max_body_size` | geprüft |
| HA-Ansichten wandeln `Unauthorized` in **401** um (`helpers/http.py`, Zeilen 103–104). Der Upload benutzt seit 12.11. den Dekorator `homeassistant.components.http.decorators.require_admin` **nicht mehr** (W-19 entfällt) | geprüft; die Aussage zum Dekorator gilt nur noch für andere Ansichten |
| HA-Aktionen (`services.py`) werden mit `async_register_admin_service` angemeldet, damit nur Administratoren sie rufen (Sicherheitsbefund U1, 12.11.) | geprüft im Code der Integration (`services.py`, Test `test_services.py`) |
| `async_sign_path` (HA-Signatur für Audio, 24 Stunden), `ban_middleware`/`process_wrong_login` bei jedem 401 einer Ansicht mit Anmeldung, `FileResponse` mit Range | geprüft im Design `ha-oberflaeche.md`, 11.4.6; Verhalten auf der festen HA-Version in A4c zu belegen |
| `handler_cancellation=True`: Trennt der Client, wird der Handler mit `CancelledError` abgebrochen (`http/server.py`, Zeile 605) | geprüft (W-03); darum `asyncio.shield` im Abschluss (5.2) |
| `request[KEY_HASS_USER]` (aus `homeassistant.components.http.const`) liefert den Nutzer | Name geprüft; Nutzung aus Wissen |
| Streaming: `request.multipart()` (aiohttp) und `part.read_chunk(size)` sind nicht durch `client_max_size` begrenzt; `read()`, `post()`, `part.read()` schon | geprüft im aiohttp-Quelltext (W-14); in AP 3.1 mit 40-MiB-Test gegen die feste Version |
| `panel_custom.async_register_panel(hass, frontend_url_path, webcomponent_name, sidebar_title, sidebar_icon, module_url, embed_iframe, config, require_admin, …)` | geprüft (Signatur) |
| Statische Dateien: `hass.http.async_register_static_paths([StaticPathConfig(...)])`; sie verlangen keine Anmeldung | Registrierung aus Wissen; fehlende Anmeldung geprüft (W-26) |
| Obergrenze „normale Anfragen 16 MiB“ | **geprüft**: `http/server.py` Zeile 69 und 278 (W-14), siehe Abschnitt 8 |
| Grenze der WebSocket-Nachricht | geprüft: HA setzt keinen Wert, es gilt die Vorgabe von aiohttp (4 MiB, aus Wissen) |
| `ffprobe`-Schlüsselnamen der Tags je Container | **offen** bis AP 3.1 (Beispieldateien von Tobias) |

## Offene Punkte für Tobias

Hier steht nur, was **nur Tobias** entscheiden oder tun kann. Alles andere hat die
Projektleitung entschieden (Tabelle oben, Abschnitt 11 bis 13); Tobias kann dort
widersprechen.

1.  **Upload über Nabu Casa (Messung am Handy).** Keine Grenze für Größe oder Dauer ist
    veröffentlicht. Bei der Abnahme der Stufe 3a lädt Tobias drei Dateien hoch (20 MiB,
    150 MiB, 500 MiB) und notiert die Dauer. Danach entscheidet er, ob `upload_max_bytes`
    steigt oder ob größere Dateien nur über den Eingang am PC kommen (D4).
2.  **Beispielmaterial für die Tags.** Vor AP 3.1 legt Tobias je zwei echte Dateien aus
    seinen Quellen bereit: ein m4b-Hörbuch, eine mp3-Hörspielfolge einer Serie, einen
    CD-Rip mit mehreren Dateien, eine Datei ganz ohne Tags. Daran belegt AP 3.1 die
    Tag-Schlüssel von `ffprobe` (11.2) und die Regeln für die Folgen-Nummer; ohne echtes
    Material bleibt die Erkennung Raten.
3.  **Zeiger beim Verschieben und Zusammenführen.** Verschiebt oder führt Tobias Folgen
    in eine andere Serie, schreibt HA die Zuordnungen der betroffenen Folgen-Tobies
    um, aber der gemerkte Hörstand auf den Boxen (`resume.json`, je Serie und Folge)
    geht für diese Tobies verloren: Sie beginnen von vorn. Der Vertrag lässt das mit
    Rückfrage zu. Die Alternative (Zeiger mitnehmen) braucht eine Änderung am Box-Dienst
    und am Datenmodell. Reicht „von vorn mit Rückfrage“?
4.  **Aktionen für Tobias (keine Entscheidung):** den Ordner `tobibox/eingang/` auf dem NAS
    anlegen und HA Schreibrecht geben (AP 3.5); die genaue HA-Patch-Version 2026.11.x
    nennen (Start AP 3.1).
