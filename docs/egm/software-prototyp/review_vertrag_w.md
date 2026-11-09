# Goldfisch-Prüfung Vertrag W (`docs/protocol/ha-websocket-v1.md`)

*   **Stand:** 09.11.2026
*   **Geprüft von:** Goldfisch ohne Vorwissen (nur Vertrag, Design, `mqtt-v1.md`, `data-model.md`, HA-Quelltext)
*   **Gegenstand:** Entwurf „Vertrag W“, Stufe 3a (AP 3.1, AP 3.2)

Schweregrade: **Hoch** = so nicht umsetzen (Datenverlust, stille Fehler oder
Lücke, die Backend und Seite auseinanderlaufen lässt). **Mittel** = vor
AP 3.1/3.2 klären. **Niedrig** = Schönheit oder Klarstellung.

Quellen für HA: Quelltext `home-assistant/core`, Zweig `dev`, abgerufen am
09.11.2026 (`components/http/server.py`, `helpers/http.py`,
`components/websocket_api/{const,http,decorators,messages,connection,commands}.py`,
`components/file_upload/__init__.py`, `components/media_source/local_source.py`,
`components/panel_custom/__init__.py`), dazu aiohttp `master`
(`web_request.py`, `multipart.py`).

## Zusammenfassung

Der Vertrag ist insgesamt gründlich und deckt AP 3.2 und die CUJs weitgehend ab.
Die HA-API-Angaben stimmen fast alle. Die größten Probleme liegen nicht bei den
Befehlen, sondern bei den **Rändern**: Wiederherstellung von HA, Abbruch und
Gleichzeitigkeit beim Upload, und zwei Stellen, an denen Seite und Backend nach
Vertrag nicht zusammenkommen (Upload-Ereignisse, Lernmodus-Wiederholung).

---

## Befunde

### Hoch

**W-01 — HA mit leerem Speicher verteilt eine leere Liste; kein Weg zurück aus dem NAS-Export**
*   **Stelle:** Abschnitt 3.8 (`liste/neu_ausrollen`), Abschnitt 1 (Export), fehlender Befehl.
*   **Problem:** `mqtt-v1.md` 5.1 sagt: Stellt die Integration beim Start fest, dass der Speicher leer ist, entsteht eine **neue Listen-ID**. Alle Boxen nehmen eine neue Listen-ID **unabhängig von der Revision** an (5.2). Wird dann eine (leere) Konfiguration veröffentlicht, löscht sie die Zuordnungen auf **allen** Boxen: Jeder Tobie spielt nur noch die Überraschungs-Serie. Der Vertrag W sagt nichts dazu, was die Integration bei leerem Speicher tut, und hat keinen Befehl, die Konfiguration aus `tobibox/export/` zurückzuholen. Das Design nennt aber genau diesen Rückweg („HA-Sicherung und NAS-Export; danach Liste neu ausrollen“).
*   **Beleg:** `mqtt-v1.md` 5.1/5.2/5.3; Design, Baustein 4 „Speicher und Medien“; Vertrag W 3.8 kennt nur „gleiche Zuordnungen“ der aktuellen Konfiguration.
*   **Vorschlag:** (a) Festlegen: Bei leerem Speicher veröffentlicht die Integration **nichts**, bis Tobias entschieden hat. (b) Neuer Befehl `tobibox/konfig/export_lesen` (zeigt Revision, Listen-ID, Zeit und Anzahl Zuordnungen des neuesten Exports) und `tobibox/konfig/aus_export` (Admin, `bestaetigt`, übernimmt die Zuordnungen mit **neuer** Listen-ID, Revision 1, veröffentlicht). (c) `hello` meldet `konfig.zustand` (`ok`, `leer_neu`, `export_neuer`), damit die Seite eine Warnung zeigt. (d) `test_restore.py` (AP 3.1) um „leerer Speicher“ erweitern.

**W-02 — Wiederherstellung aus Sicherung mit alter Listen-ID: Boxen lehnen still ab, HA merkt es nicht**
*   **Stelle:** Abschnitt 3.7 (`konfig_stand`), 3.8, 4.5, Abschnitt 2.2/Fragestellung „Sicherung“.
*   **Problem:** Wird HA aus einer Sicherung mit **alter Listen-ID und niedrigerer Revision** zurückgespielt, lehnen die Boxen jede neue Liste mit `revision_zu_niedrig` ab, bis die Revision die der Box übersteigt. `zuordnung/set` antwortet derweil mit Erfolg und `veroeffentlicht=true` (der Broker hat sie ja). Tobias sieht nur: „Zuordnung gespeichert“, die Box spielt weiter das Alte. Dazu: `konfig_stand` kennt nur `aktuell` und `veraltet`. Eine Box mit **höherer** Revision als HA (genau dieser Fall) wäre „veraltet“, obwohl sie in Wahrheit voraus ist. Das führt in die falsche Richtung.
*   **Beleg:** `mqtt-v1.md` 5.2/5.3; Vertrag W 3.7 (`konfig_stand`), 3.5 (`zuordnung/set`).
*   **Vorschlag:** `konfig_stand` um `voraus` ergänzen (gleiche `liste_id`, Box-Revision > HA-Revision) und in `boxen/list` sowie im Ereignis `boxen` melden. Die Seite zeigt dann „Die Box hat einen neueren Stand als HA. Bitte ‚Liste neu ausrollen‘ (oder aus dem Export holen).“ Zusätzlich: Die Integration soll bei `voraus` oder `liste_abgelehnt` mit `revision_zu_niedrig` ein Ereignis `konfig` `art="abweichung"` senden. Die Revision beim Zurückspielen nicht „automatisch erhöhen“ (würde gegen die Boxen laufen).

**W-03 — Upload: Abbruch mitten im Abschluss und Wettlauf bei gleichem Namen**
*   **Stelle:** 5.2 Schritte 3–5, 5.3 (`datei_existiert`), 5.6.
*   **Problem:**
    1.  HA startet seine Webanwendung mit `handler_cancellation=True` (`http/server.py`, Zeile 605): Trennt der Client, wird der Handler **abgebrochen** (`CancelledError`). Der Abschluss (Prüfung bis 30 s, `os.replace`, Eintrag in `serie.json`) ist nicht „atomar“ gegen diesen Abbruch. Die Datei kann umbenannt, `serie.json` aber nicht fortgeschrieben sein (oder umgekehrt). Der Vertrag verspricht „ein abgebrochener Versuch hinterlässt keine Datei und keinen Eintrag“. Das stimmt hier nicht. Die Wiederholung bekommt dann `datei_existiert`, und 5.6 hilft nicht, weil das Ergebnis nur im Speicher steht und nicht geschrieben wurde.
    2.  Es steht nirgends, dass der Abschluss unter der Sperre der Serie läuft. Zwei Uploads mit gleichem Namen (zwei Tabs, zwei Handys) prüfen beide „existiert nicht“, und `os.replace` **überschreibt** still. Auf einer SMB-Freigabe (QNAP) ist die Namensprüfung meist **ohne Groß-/Kleinschreibung** und Unicode-NFC/NFD kann verschieden sein: `Folge.MP3` und `folge.mp3` sind dort dieselbe Datei.
    3.  Zwei gleichzeitige Uploads mit **gleicher `upload_id`** schreiben in dieselbe `.part`-Datei.
*   **Beleg:** `http/server.py` Zeile 605; HA-Vorbild `file_upload/__init__.py` fängt `Exception, CancelledError` ab und räumt auf.
*   **Vorschlag:** Abschluss (Prüfung, Umbenennen, `serie.json`, Ergebnis merken) als eigene Aufgabe mit `asyncio.shield` starten, damit ein Abbruch ihn nicht halbiert; die Aufräumarbeit steht in `finally`/`except CancelledError`. Den Abschluss unter der Sperre der Serie ausführen. Statt `os.replace` ohne Prüfung: erst `os.link`/`O_EXCL`-Anlegen oder Prüfung ohne Groß-/Kleinschreibung unter der Sperre. Das Ergebnis je `upload_id` für 1 Stunde merken, **auch wenn der Client weg ist**. Die Seite fragt nach einem Fehler per `serie/get` nach, ob die Datei da ist. `.part`-Name immer mit Zufallsanteil (nie nur die `upload_id`), zweiter Upload mit gleicher `upload_id` während der erste läuft: Fehler `upload_laeuft`.

**W-04 — Ereignisse `upload` können nicht zugeordnet werden**
*   **Stelle:** 4.6, 5.3 (`upload_id`), 3.1 (`subscribe`).
*   **Problem:** 4.6 sagt, Ereignisse gehen nur an die Verbindung, die den Upload gestartet hat, „Zuordnung über `upload_id`“. Die `upload_id` kommt aber nur im HTTP-Körper an, nicht über die WebSocket-Verbindung. Das Backend kennt keine Verbindung zu dem Upload. Es gibt keinen Befehl `upload/anmelden`.
*   **Vorschlag:** Entweder (einfach) Ereignisse an **alle** Abos des gleichen Nutzers mit `thema=upload` schicken; die Seite filtert nach `upload_id`. Oder (aufwendiger) einen Befehl `tobibox/upload/anmelden` mit `upload_id`. Empfehlung: Variante 1. Dann `snapshot` und der Satz „nur für Uploads dieser Verbindung“ ändern. Außerdem: Das Ereignis `empfange` doppelt, was der Browser selbst misst (5.7); es kann entfallen, übrig bleiben `pruefe`, `fertig`, `fehler`.

**W-05 — Lernmodus: erneutes „Start“ liefert einen toten Vorgang**
*   **Stelle:** 3.6 `lernmodus/start` (Idempotenz), 6.2.
*   **Problem:** Die Box lernt höchstens 2 min ab Eintreffen des Befehls, das Backend hält den Vorgang aber bis `frist_bis` = Beginn + 180 s offen. Drückt Tobias nach etwa 130–180 s noch einmal „Lernmodus“ mit gleichem Ziel, liefert das Backend „den laufenden Vorgang“ und sendet **keinen** Befehl. Die Box lernt aber schon nicht mehr. Das Kind legt den Tobie auf, nichts passiert (nur die Box-Meldung `unbekannt`).
*   **Beleg:** `mqtt-v1.md` 3.7/4.2 (Box misst 2 min selbst); Vertrag W 3.6.
*   **Vorschlag:** Das Backend beendet den Vorgang `abgelaufen`, sobald `status.lernmodus=false` nach einem Status mit `lernmodus=true` ankommt (der Status hat das Feld), spätestens Beginn + 130 s. Nur `frist_bis` für die späte Meldung (Funktechnik, Verbindungsabbruch) behalten. Beim erneuten Start mit gleichem Ziel nur dann den alten Vorgang liefern, wenn der letzte Status `lernmodus=true` sagt.

### Mittel

**W-06 — Reihenfolge „Speichern, Export, Veröffentlichen“ (Abschnitt 1)**
*   **Problem:** Der Export auf das NAS steht **vor** dem Veröffentlichen. Hängt das NAS (SMB, Standby), verzögert oder blockiert das die Verteilung. Bei Entscheidung H wartet die Box nur 10 s auf die Konfiguration. Zugleich nennt keine Fehlerliste den Fall „Export schlägt fehl“; fällt er still weg, ist das Sicherheitsnetz (W-01) weg, und niemand merkt es.
*   **Vorschlag:** Speichern, **Veröffentlichen**, dann Export (im Hintergrund, mit Wiederholung). Ein Fehler beim Export bricht den Befehl nie ab, wird aber gemeldet: `konfig.export_ok` (bool) und `export_geschrieben_am` in `konfig` (hello, `zuordnung/list`), Ereignis `konfig`.

**W-07 — „Erst Konfiguration, dann `ack`“ braucht eine Bedingung (Entscheidung H) und Fehlerwege**
*   **Stelle:** 6.2 Schritt 4, 3.6 `lernmodus/antwort`.
*   **Problem:** (a) Der Vertrag sagt nicht, dass das `ack` erst nach dem **PUBACK** der Konfiguration gesendet wird. Zwei getrennte Veröffentlichungen halten bei QoS 1 die Reihenfolge bei Neuübertragung nicht garantiert. (b) Ist der Broker weg (`veroeffentlicht=false`), muss das `ack` **zurückgehalten** werden; sonst löscht es den Eintrag auf der Box vor der Konfiguration. (c) Was passiert bei `konfig_zu_gross`, Schreibfehler oder einer inzwischen verschwundenen Serie im Schritt 4? Weder Zustand noch `ack` sind festgelegt (`grund` im Ereignis kennt nur `nutzer`, `abgelaufen`). (d) Bei „Ziel schon genau das bestehende“ (Schritt 4) lässt `ack zugeordnet` die Box bis zu 10 s schweigen (`mqtt-v1.md` 4.2: nur `abgelehnt` beendet das Warten). Das wird als gewollt beschrieben, ist aber 10 s Stille für das Kind.
*   **Vorschlag:** (a)+(b) „Das `ack` folgt dem PUBACK der Konfiguration; ohne PUBACK kein `ack`; die Meldung bleibt retained und wird nach der Frist abgelehnt.“ (c) `abgelehnt` mit `grund` `konfig_zu_gross`, `speicherfehler`, `ziel_fehlt` aufnehmen, Ereignis `lernmodus` `abgelehnt` mit Klartext. (d) Entweder hinnehmen und in der Seite sagen („Der Tobie hat dieses Ziel schon“), oder mit der Projektleitung klären, ob `abgelehnt` hier der bessere Weg ist.

**W-08 — Erneute Lieferung der Meldung `gelernt` nach Neustart: `abgelehnt` obwohl zugeordnet**
*   **Stelle:** 6.2 Schritt 3.
*   **Problem:** Der Vorgang steht nur im Arbeitsspeicher. Stürzt HA ab, nachdem die Zuordnung gespeichert wurde (aber vor dem `ack`), kommt die retained Meldung erneut an, der Vorgang ist weg, das Backend bestätigt `abgelehnt`. Die Zuordnung besteht aber (und wird dann in „Neue Tobies“ als doppelt geführt, siehe W-11). Auch das gleiche Ereignis zweimal (QoS 1) wird als „kein Vorgang“ behandelt.
*   **Vorschlag:** Die letzten 20 abgeschlossenen Vorgänge (`befehl_id`, Ergebnis, `uid`) im HA-Speicher festhalten. Kommt dieselbe `befehl_id` mit `zugeordnet` erneut, `ack zugeordnet` wiederholen.

**W-09 — Rückfrage-Frist und fehlende Benachrichtigung**
*   **Stelle:** 6.2 Schritt 3, Festlegung 7, offener Punkt 11.
*   **Problem:** Die Rückfrage hat als Frist `frist_bis` (Beginn + 180 s). Kommt die Meldung spät (z. B. nach 170 s), bleiben Tobias 10 s zum Antworten. Die Rückfrage erscheint nur, wenn die Seite offen ist (Ereignis); ist sie zu, läuft sie unbemerkt ab, kein Hinweis in HA.
*   **Vorschlag:** Eigene Frist für die Rückfrage: `rueckfrage_bis = max(frist_bis, Meldung + 60 s)`. Persistente Benachrichtigung in HA bei Rückfrage (gleiche Technik wie bei `befehl_abgelehnt`).

**W-10 — Befehle über HA-Aktionen und `ui/*`-Themen sind nicht im Vertrag**
*   **Stelle:** Abschnitt 1 („Alles außer dem Hochladen läuft über WebSocket“), 2.3.
*   **Problem:** Das Design nennt Aktionen (`services.yaml`, auch für Automationen: zuordnen, lösen, Lernmodus, Sync, Liste neu ausrollen …) und `mqtt-v1.md` 3.8 die Knöpfe `ui/sync`, `ui/lernen_abbrechen`, `ui/update`, `ui/lern_serie`. Der Vertrag sagt nicht, dass sie **dieselben** Backend-Funktionen aufrufen (Sperre, Revision, Reihenfolge H, Vorgang), und nicht, was die Rückfrage für einen per Aktion gestarteten Lernmodus bedeutet (keine Seite, kein Antwortweg).
*   **Vorschlag:** Ein Satz: „Aktionen und `ui/*` rufen dieselben Funktionen wie die Befehle. Bei einer Aktion ohne Seite gilt bei Rückfrage `ueberschreiben=false`, also `abgelehnt`, es sei denn, das Aktionsfeld `ueberschreiben=true` ist gesetzt.“ Und `ui/lernen_abbrechen` beendet den Vorgang wie `lernmodus/abbrechen`.

**W-11 — „Neue Tobies“: bereits zugeordnete Kennung wird wieder aufgenommen**
*   **Stelle:** 3.4, 6.1; `mqtt-v1.md` 3.6 (`bekannt`).
*   **Problem:** Ein Tobie, den eine Box noch als `unbekannt` gemeldet hat (Box war lange offline und hatte die Zuordnung nicht), trifft ein, nachdem Tobias ihn zugeordnet hat. 3.4 sagt: „Meldet eine Box die Kennung erneut, erscheint sie wieder.“ Dann steht eine bereits zugeordnete Kennung in der Liste „Neue Tobies“. Der Vertrag legt auch nicht fest, ob `bekannt` „schon in der Liste“ oder „schon zugeordnet“ heißt. Außerdem: `anzahl` „Summe der Meldungen“ kann doppelt zählen, wenn das Backend bei jeder Nachricht addiert; die Zahl der Nachricht ist je Box schon die Summe.
*   **Vorschlag:** Ist die Kennung in `zuordnungen`, wird sie **nicht** aufgenommen, `ack bekannt`. Hinweis an die Seite über das Ereignis `boxen` (Box hat die Liste noch nicht: `konfig_stand=veraltet`). `anzahl` je Box ersetzen, nie addieren.

**W-12 — `zuordnung/set`/`remove` ohne Konflikterkennung bei zwei Tabs**
*   **Stelle:** 1 („Die Seite braucht dafür keine eigene Revision zu schicken“), 3.5.
*   **Problem:** Ohne `ueberschreiben` schützt `zuordnung_existiert` beim **ersten** Zuordnen. Beim bewusst gesendeten `ueberschreiben=true` (Ändern einer bestehenden Zuordnung) und bei `remove` gilt „letzter gewinnt“. Tab A ändert Tobie X auf Serie 1, Tab B (altes Bild) ändert X auf Serie 2 oder löst X. Das Verhalten ist im Vertrag nicht als Entscheidung festgehalten (`stand` gibt es nur für Medien). Ähnlich: `folgen/order` und `folge/delete` haben `stand` **optional**; wenn die Seite ihn weglässt, schützt nichts.
*   **Vorschlag:** Optionales Feld `erwartet_ziel` (Ziel oder `null`) bei `zuordnung/set`/`remove`; Abweichung: `zuordnung_geaendert` (409). Für `folgen/order`: Die Seite **muss** `stand` senden (im Vertrag als „muss“, im Schema optional lassen, damit Aktionen funktionieren).

**W-13 — Größen: 64 KiB gegen 256 KiB; `zuordnung/list` ohne Seiten**
*   **Stelle:** Abschnitt 8, Zeile 2; 3.5 `zuordnung/list`; offener Punkt 16.
*   **Problem:** Der Vertrag setzt 64 KiB je gesendeter Nachricht und lässt `zuordnung/list` bis 256 KiB zu. Das widerspricht sich. In HA gibt es keine feste Grenze für ausgehende WebSocket-Nachrichten (nur die Warteschlange, `MAX_PENDING_MSG = 4096`); 64 KiB ist eine eigene Wahl. Das ist kein Punkt für Tobias, sondern eine Vertragsfrage.
*   **Vorschlag:** `limit`/`offset` bei `zuordnung/list` **jetzt** aufnehmen (additiv, ändert nichts), oder die Grenze für diesen Befehl auf 256 KiB setzen und das so schreiben.

**W-14 — Die 16-MiB-Grenze ist im Quelltext vorhanden; Aussage des Vertrags falsch**
*   **Stelle:** Abschnitt 8, Zeile „Normale HTTP-Anfragen“; „Prüfung gegen die HA-API“, letzte Zeilen; offene Punkte 19.
*   **Problem:** Der Vertrag schreibt „Stelle im Quelltext nicht gefunden“. Sie ist da: `homeassistant/components/http/server.py`, Zeile 69, `MAX_CLIENT_SIZE: Final = 1024**2 * 16`, genutzt in Zeile 278 (`client_max_size=MAX_CLIENT_SIZE`). Eine Forumsmeldung für 2026.7/2026.8 („Maximum request body size 16777216 exceeded“, Issue #177999, „not a bug“) bestätigt es. Weiter: Das Streaming mit `read_chunk` ist in aiohttp **nicht** begrenzt (die Grenze gilt für `read()`, `post()` und `part.read()`), die Aussage 5.1 stimmt also; aber `part.read()`/`part.text()` für das Feld `upload_id` sind auf `client_max_size` begrenzt (hier harmlos). HA-eigene Uploads setzen die Grenze trotzdem je Ansicht (`file_upload`: `_client_max_size = 100 MiB`; `media_source`: 20 MiB). `HomeAssistantView.max_body_size` existiert (`helpers/http.py` Zeile 139) und wirkt vor dem Handler.
*   **Vorschlag:** Zeile korrigieren und mit Fundstelle belegen. Für die Ansicht `max_body_size` **nicht** erhöhen, solange nur gestreamt wird; im Test (AP 3.1) ein Upload deutlich über 16 MiB (z. B. 40 MiB), um sicher zu sein, dass die aiohttp-Version der festen HA-Version das Streaming nicht begrenzt.

**W-15 — Nabu Casa: Risiko ernster nehmen, Grenzwerte vorsichtiger setzen**
*   **Stelle:** 5.8, Abschnitt 8 (Nabu Casa; Token), offener Punkt 20, `upload_max_bytes` 2 GiB.
*   **Problem:** Eine dokumentierte Größen- oder Zeitgrenze für Uploads über Nabu Casa fand sich **nicht** (Suche, 09.11.). Es gibt Forenberichte, dass der Durchsatz über Nabu Casa niedrig ist (nur mündlich genannt, nicht belegt). Dann dauert eine 2-GiB-Datei sehr lange, und: (a) Die Antwort kommt erst nach der Prüfung (bis 30 s ohne Datenfluss), (b) das Handy kann in den Ruhezustand gehen, (c) das Token (30 min) gilt für den Start. Das Token ist der kleinste Punkt, die Dauer der größte.
*   **Vorschlag:** `upload_max_bytes` zunächst klein ansetzen (z. B. 500 MiB; ein Hörspiel ist meist 50–200 MiB) und erst nach der Abnahme anheben. Die Seite zeigt Fortschritt und bei Abbruch „erneut senden“ (kein Fortsetzen in v1, Vertrag sagt das schon). Im Abnahmetest drei Größen: 20 MiB, 150 MiB, 500 MiB über Nabu Casa mit Messung der Dauer.

**W-16 — Sicherheit beim Prüfen mit `ffprobe`**
*   **Stelle:** 5.4.
*   **Problem:** `ffprobe` wird auf eine fremde Datei losgelassen, **bevor** das Format feststeht. ffmpeg erkennt Formate am Inhalt, nicht an der Endung: Eine Textdatei mit Playlist (HLS/`concat`) kann auf andere Dateien oder Netzadressen verweisen (Lesen lokaler Dateien, Netzzugriffe aus HA). Der Vertrag nennt nur Zeitlimit.
*   **Vorschlag:** Aufruf mit `-protocol_whitelist file` (oder `pipe`), Format erzwingen (`-f` aus der Endung abgeleitet) und danach `format_name` gegen eine Liste prüfen; mindestens ein Audio-Strom; Zeitlimit und Speicherlimit; Aufruf als Liste (keine Shell), Dateiname nie in einer Shell-Zeile. Das als Pflicht in 5.4 schreiben.

**W-17 — Namen und Ordner: Sonderzeichen der Freigabe, reservierte Namen**
*   **Stelle:** 3.2 `serie/create` (Ordnername), 5.3 (Dateiname), offener Punkt 14.
*   **Problem:**
    *   Der Dateiname darf `:` `?` `*` `"` `<` `>` `|` enthalten (nur `/` und `\` sind verboten). Auf einer SMB/CIFS-Freigabe (QNAP) schlägt das Anlegen fehl oder wird abgebildet. `Folge 1: Der Rabe.mp3` ist ein sehr üblicher Titel. Ergebnis: `medien_schreibfehler` (500) ohne erklärbaren Grund.
    *   Steuerzeichen (z. B. NUL, Zeilenumbruch) sind im Dateinamen nicht ausgeschlossen (beim Ordnernamen schon).
    *   Ordnername aus dem Namen: „Punkt am Anfang entfällt“. Bei `...` bleibt nichts übrig (leerer Name). Ein Ende mit Punkt oder Leerzeichen (Windows-Regel) und das Kürzen auf 255 **Bytes** kann ein UTF-8-Zeichen halbieren.
    *   `medien/_papierkorb/` und `medien/_upload/` sind Ordner **ohne** `serie.json` im Medienordner. Nach `data-model.md` (Ordner ohne `serie.json`) würden sie als Serien erkannt, auch von der Prüfung der Integration. Die Namen sind nirgends reserviert; eine Serie „_upload“ kollidiert.
*   **Vorschlag:** Einen Abschnitt „Namen“: erlaubte Zeichen = Zeichen, die die Freigabe zulässt (Verbot `:*?"<>|`, Steuerzeichen, Ende mit Punkt/Leerzeichen); statt Ablehnung bietet die Seite einen Vorschlag („Folge 1 - Der Rabe.mp3“). Reservierte Namen `_papierkorb`, `_upload` (alle Ordner mit `_` am Anfang) werden von Prüfung und Box ignoriert. Kürzen an Zeichengrenzen. Die Namenslänge auf der SMB-Freigabe ist 255 UTF-16-Einheiten, nicht Bytes; kürzere der beiden Grenzen nehmen.

**W-18 — Kopie: Papierkorb-Wiederherstellung und `data-model.md`**
*   **Stelle:** 3.3, offene Punkte 15.
*   **Problem:** Das Format der Papierkorb-Hilfsdatei ist offen, `restore` baut aber darauf. Der Vertrag setzt auch voraus, dass Verschieben nach `_papierkorb` ein atomares Umbenennen auf demselben Dateisystem ist (stimmt, wenn `_papierkorb` auf derselben Freigabe liegt). Zwei Löschungen gleicher Folge/Datei nacheinander: Name im Papierkorb eindeutig? (Eintrag-ID als Ordner, nicht Name.)
*   **Vorschlag:** Papierkorb je Eintrag ein Ordner `_papierkorb/<id>/` mit `meta.json` und der Datei. Das ist kein Punkt für Tobias, sondern für die Projektleitung und `data-model.md` (additiv).

### Niedrig

**W-19 — HTTP-Status 403 gegen HA-Verhalten:** Die Tabelle in 2.1 und Abschnitt 7 sagt für Nicht-Admin am Upload 403. HA-Ansichten wandeln `Unauthorized` in **401** um (`helpers/http.py`, Zeilen 103–104); der fertige Dekorator `homeassistant.components.http.decorators.require_admin` macht das. Entweder 401 hinnehmen oder 403 selbst senden. Empfehlung: Dekorator benutzen, Tabelle „401 oder 403“ nennen, die Seite wertet in beiden Fällen den `code` aus.

**W-20 — `veroeffentlicht` bei `geaendert=false`:** Nicht festgelegt (es gibt keine Veröffentlichung). Vorschlag: `null`.

**W-21 — Wortwahl „Sperre je Ziel“ (Abschnitt 1):** „Ziel“ ist im Vertrag der Zuordnungs-Begriff. Besser „Sperre für die Konfiguration und je Serie“.

**W-22 — `anfrage_id` und Fehler:** Wiederholt die Seite mit gleicher `anfrage_id` nach einem Fehler (z. B. `mqtt_nicht_verbunden`), darf nicht der gemerkte Fehler zurückkommen. Nur Erfolge merken.

**W-23 — Ereignisse zusammenfassen:** „Höchstens ein Ereignis je Thema und Box und Sekunde“ würde `boxen`/`ereignis` (jede Meldung wie `liste_abgelehnt`) verschlucken. Vorschlag: Zusammenfassen nur für `geaendert`, `ereignis` und Lernmodus-Zustände nicht.

**W-24 — `lernmodus/abbrechen` bei offener Rückfrage:** Der Text sagt „Meldung, die danach eintrifft“ → `abgelehnt`. Bei einer **schon eingetroffenen** Meldung mit offener Rückfrage muss das `ack abgelehnt` sofort beim Abbrechen gesendet werden. Klarstellen.

**W-25 — `box_offline` bei `online=null`:** Nicht festgelegt (HA kennt noch nichts). Vorschlag: wie `offline`, mit Klartext.

**W-26 — Statische Dateien sind öffentlich:** Mit `async_register_static_paths` ausgelieferte Dateien verlangen in HA keine Anmeldung. Der Vertrag soll sagen: Die Seite enthält keine Geheimnisse (Passwörter, Adressen). Ebenso: Namen von Serien und Folgen aus dem Dateisystem darf die Seite nur als Text, nie als HTML darstellen (Lit tut das von selbst).

**W-27 — Lesezugriff für alle Nutzer:** Wirkt gewollt, aber `hello` verrät Version und Box-Namen auch Nicht-Admins. Harmlos in diesem Haushalt, nur im Vertrag nennen.

**W-28 — `serien/list` aus Zwischenspeicher:** Liest der Befehl alle `serie.json` neu von der Freigabe (SMB, kann schlafen), reißt er die 10 s. Festlegen: Antwort aus dem Zwischenspeicher der letzten Prüfung (`geprueft_am` zeigt das schon), nur `serie/get` liest frisch.

---

## Zu den Prüffragen

### 1. Vollständigkeit
*   AP 3.2 (Serienliste, Folgen ziehen, Hochladen, Umbenennen, Neue Tobies, Lernmodus mit Serie/Folge, Zuordnen mit Typ, Aktionskarten, Box-Status mit freiem Speicher, „Liste neu ausrollen“, „Papierkorb leeren“) ist durch die Befehle 3–23 gedeckt.
*   CUJ 7a/7b/9/10/11/12: gedeckt (Status, `letzter_fehler`, `update`, `sync` stehen unverändert in `boxen/list`). CUJ 10 hat nur reservierte Namen (3b), das ist richtig.
*   **Fehlt:** Import aus dem Export und Warnung bei leerem Speicher (W-01), Zustand `voraus` (W-02), Export-Status (W-06), Anmeldung für Upload-Ereignisse (W-04), Hinweis auf Aktionen/`ui/*` (W-10).
*   Fehlendes Feld: `konfig.export_ok`, `konfig_stand=voraus`, `upload_laeuft` (Fehlercode).

### 2. Widersprüche
*   **Revisionsregel und Listen-ID:** `liste/neu_ausrollen` (Revision 1, neue ID) entspricht `data-model.md` Abschnitt 2 und `mqtt-v1.md` 5. Kein Widerspruch. Lücke: Verhalten bei leerem Speicher (W-01) und bei Box mit höherer Revision (W-02).
*   **Reihenfolge Konfiguration vor `ack` (Entscheidung H):** im Grundsatz richtig übernommen, aber ohne PUBACK-Bedingung und ohne Fehlerwege (W-07).
*   **Ablaufzeiten:** `lernen` 60 s, `lernen_abbrechen` 30 s, `sync` 300 s, `update` 300 s und `frist_bis` = 60 + 120 s stimmen mit `mqtt-v1.md` 3.7/4.2 überein. Problem nur bei der Wiederverwendung des Vorgangs (W-05).
*   **`ziel` in `config.json` Version 2:** Feldnamen (`typ`, `serie`, `folge`, `aktion`; `aktion` ∈ `status`, `gute_nacht`) stimmen mit `data-model.md` 2 überein.
*   **`unknown.json` und Bestätigung:** `ack` mit `zuletzt` und `art`, `neu`/`bekannt`/`zugeordnet`/`abgelehnt`, Löschen erst nach `ack`: übereinstimmend. Offen: `bekannt` bei schon zugeordneter Kennung (W-11).
*   **Interner Widerspruch:** 64 KiB gegen 256 KiB (W-13).

### 3. Umsetzbarkeit in HA (geprüft am Quelltext, 09.11.2026)
*   `websocket_command` (Schema, Befehlsname), `async_response`, `require_admin` (wirft `Unauthorized`, Dekoratorreihenfolge wie im Vertrag möglich, da `wraps` die Marker übernimmt): **stimmt**.
*   Schema und unbekannte Felder: `BASE_COMMAND_MESSAGE_SCHEMA` nur mit `id`; das Schema des Befehls lehnt unbekannte Felder ab (`invalid_format`): **stimmt** (die Bibliothek heißt in `dev` `probatio`, siehe Vertrag).
*   Fehlerformat `code`/`message` (dazu optionale Übersetzungsfelder), `send_error`, `send_result(msg_id, result=None)`: **stimmt**.
*   Abos: `connection.subscriptions[msg["id"]]`, `unsubscribe_events`: **stimmt**.
*   Größen: `WebSocketResponse(heartbeat=55, decode_text=False)` (kein eigenes `max_msg_size`, also aiohttp-Vorgabe), `MAX_PENDING_MSG = 4096`: **stimmt**.
*   `HomeAssistantView`: `requires_auth=True`, `cors_allowed=False`, `max_body_size=None`: **stimmt**; nicht angemeldete Anfrage → `HTTPUnauthorized` vor dem Handler, der Körper wird nicht gelesen: **gut**. Status bei Nicht-Admin: siehe W-19.
*   Streaming: `request.multipart()` und `read_chunk` sind nicht durch `client_max_size` begrenzt (nur `read()`/`post()`/`part.read()`); HA selbst streamt so (`file_upload`, 1-MiB-Blöcke, Schreiben im Executor, Aufräumen bei Abbruch). **Stimmt**, mit den Ergänzungen aus W-03 und W-14.
*   **16 MiB:** vorhanden (W-14).
*   `panel_custom.async_register_panel(...)` mit `require_admin: bool = False`: Signatur **stimmt**. `require_admin` blendet nur die Seitenleiste/das Panel aus, ersetzt nicht die Prüfung im Backend (Vertrag sagt das richtig).
*   **Nabu Casa:** keine veröffentlichte Grenze gefunden; bekannte Einschränkungen nur als Forenberichte zum Durchsatz (W-15). Offen bis zur Abnahme am Handy.

### 4. Robustheit
*   **Doppeltes Senden:** gut gelöst (`anfrage_id`, `upload_id`, Endzustand). Kleinigkeit W-22.
*   **Zwei Tabs:** Medien gut (`stand`), Zuordnungen nicht (W-12).
*   **Abbruch eines Uploads:** W-03.
*   **Broker offline:** Änderungen werden gespeichert, `veroeffentlicht=false`: gut. Nachholen und `ack`-Zurückhalten fehlen (W-07). Wer „holt nach“ und wie oft, steht nicht im Vertrag: bei Wiederverbinden die aktuelle Konfiguration neu veröffentlichen (retained, Revisionsregel schützt).
*   **Zwei Boxen:** Neue Tobies (ein Eintrag) gut; Vorgang je Box gut; `anzahl` (W-11).
*   **Lernmodus mit Rückfrage und Frist:** W-05, W-08, W-09, W-24.
*   **HA aus Sicherung:** W-01, W-02.

### 5. Sicherheit
*   **Pfad-Traversal Dateiname:** `/`, `\`, `.`, `..`, führender Punkt sind ausgeschlossen; das genügt für Traversal. Ergänzen: Steuerzeichen/NUL, Sonderzeichen der Freigabe (W-17).
*   **Serien-ID in der URL:** nur als Schlüssel nachschlagen, nie in den Pfad setzen; für Ordner ohne `serie.json` ist die ID der Ordnername. Im Vertrag ergänzen: „Pfad aus der Serien-Tabelle, nie aus der Eingabe.“
*   **Ordnername aus Serienname:** Ersetzen von `/` und `\` ist richtig; die Randfälle sind in W-17.
*   **Rechte:** Konzept (Lesen alle, Schreiben Admin) ist stimmig und mit dem Quelltext umsetzbar. Statische Dateien öffentlich (W-26).
*   **Upload ohne Anmeldung:** HA lehnt vor dem Handler ab (401). Gut.
*   **Dateitypen:** Endung plus Inhaltsprüfung gut; die Härtung von `ffprobe` fehlt (W-16). Auch fehlt eine Obergrenze für gleichzeitige Uploads und eine Prüfung des freien Platzes **vor** dem Start (Speicher zweimal: `Content-Length` gegen freien Platz, sonst 507 erst am Ende).
*   **CSRF:** nicht relevant (Bearer-Header, kein Cookie).

### 6. Offene Punkte für Tobias
Aus den Quellen schon beantwortbar oder keine Entscheidung von Tobias:

| Nr. | Urteil |
|---|---|
| 1 Seite für Nicht-Admins | Mit Entscheidung D (Tobias einziger Benutzer) beantwortbar: `require_admin=True`. Kein Punkt für Tobias. |
| 2 „Bestätigen“ | Das Wort steht im Design nur für das `ack`. Frage an Tobias unnötig, wenn nicht aus einem Gespräch bekannt. |
| 3 Folge umbenennen | D4 nennt nur „Serien anlegen und umbenennen“. Der Satz bei der Seite („Folgen … sortieren, löschen, umbenennen“) ist mehrdeutig. Teilweise beantwortbar: v1 ohne Folgen-Umbenennen; nur kurz bestätigen lassen. |
| 4 `serie/delete` | D4: nicht im Umfang. Beantwortet. |
| 5 Löschen mit Zuordnung | Design: Papierkorb ist umkehrbar. Vorschlag stimmig. Echte Entscheidung, aber klein. |
| 6 Maximale Dateigröße | Echt offen, aber W-15 beachten (kleiner anfangen). |
| 7 Gleicher Dateiname | Echte Geschmacksfrage. |
| 8 Kopierschutz | Beantwortet durch D5 („warnt“). |
| 9 Folgen-Ordner von der Seite | Beantwortet durch D4 und Entscheidung F (kommen vom PC). |
| 10 Namen für Tobies | Echte Entscheidung (Datenmodell, additiv). |
| 11 Rückfrage-Frist | Technisch, siehe W-09; kein Punkt für Tobias. |
| 12 Zweiter Lernmodus | Echt offen, klein. |
| 13 Überraschungs-Serie anlegen | Beantwortet durch D4 („Überraschungs-Serie befüllen“); anlegen ist eine Folge davon. |
| 14 `_upload`/`_papierkorb` aus dem Sync | Kein Punkt für Tobias: Aufgabe der Projektleitung für AP 3.4/3.5 und `data-model.md` (siehe W-17). |
| 15 Papierkorb-Metadaten | Kein Punkt für Tobias, siehe W-18. |
| 16 Viele Zuordnungen | Technisch, siehe W-13. |
| 17 Aufbewahrung der Box-Meldungen | Technisch; Vorschlag reicht. |
| 18 Leise-Zeiten in 3a | Beantwortet durch das Design (AP 4.7 in Stufe 4). |
| 19 HA-Version | Echt offen (Tobias nennt sie), aber die 16-MiB-Grenze ist inzwischen belegt (W-14). |
| 20 Nabu Casa | Echt offen, nur am Handy prüfbar. |

**Weitere offene Punkte, die fehlen:** (a) Was passiert bei leerem HA-Speicher (W-01); (b) wer schützt gegen eine Box mit höherer Revision (W-02); (c) Obergrenze für gleichzeitige Uploads und Platzprüfung; (d) Verhalten bei Namen mit Sonderzeichen (W-17); (e) Benachrichtigung bei Rückfrage (W-09); (f) Export-Fehler sichtbar machen (W-06).

---

## Geprüft, ohne Befund

*   Befehls- und Feldnamen des Ziels (`typ`, `serie`, `folge`, `aktion`) gegen `data-model.md` 2 und `mqtt-v1.md` 3.1.
*   Listen-ID als 16 Zeichen `[0-9a-f]`, Revision ab 1, Verhalten bei neuer Listen-ID gegen `mqtt-v1.md` 5.2.
*   Lebensdauern der Befehle (`lernen` 60, `lernen_abbrechen` 30, `sync` 300, `update` 300) und `ttl_s`-Bereich.
*   `ack`-Felder (`zuletzt`, `art`, `grund`) und Löschregel der Box gegen `mqtt-v1.md` 3.6 und `data-model.md` 4.
*   `lernen_abbrechen` auch bei unsicherer Uhr, keine `befehl_abgelehnt`-Antwort darauf; Vertrag setzt kein `box_offline`: stimmig mit 3.7.
*   Fehlercode `zeit_unsicher` als Grund `box_lehnt_ab`: stimmt mit `mqtt-v1.md` 3.4.
*   Folge-Objekt: `datei`/`ordner`, Name als Schlüssel, Natürliche Sortierung (`data-model.md` 5).
*   Serien-ID: zufällig 12 Zeichen, Ordnername als ID bei Ordnern ohne Datei, doppelte ID (jüngere Kopie).
*   Überraschungs-Serie (`ok`, `fehlt`, `mehrere`, `leer`) gegen `data-model.md` 5.
*   Endungsliste der Uploads gleich der Liste in `data-model.md`.
*   Zuordnung auf Serie, die noch nicht auf der Box ist (zulässig laut Design/`data-model.md` 2).
*   Folge löschen lässt die Zuordnung stehen, Box spielt Überraschung (`folge_fehlt`).
*   Rechte-Konzept (Lesen/Schreiben) und die Art der Umsetzung (`require_admin`, Reihenfolge der Dekoratoren) gegen den Quelltext.
*   Ereignisform `{"id","type":"event","event":…}`; Abo-Ende mit `unsubscribe_events`; Snapshot nach der Antwort.
*   WebSocket: 4 MiB Eingangsgrenze (aiohttp-Vorgabe), `heartbeat=55`, `MAX_PENDING_MSG=4096`.
*   Upload: nur Streaming, nie `read()/post()/json()`; Anmeldung vor dem Handler; kein CSRF-Problem.
*   Idempotenz-Tabelle der 23 Befehle (Spalte „Doppelt gesendet“) in sich stimmig.
*   Versionierung (`hello`, strengere Eingaben, neuer Wurzelname bei `v2`) passt zu `mqtt-v1.md` 8.
*   Reservierte Befehle (Abschnitt 10) widersprechen dem Design nicht (Leise-Zeiten Stufe 4, Update 3b, Lautheit ohne Befehl, D6).
*   Begriff „Tobie“/„Tobies“ in den Texten für Eltern (Entscheidung F1).
