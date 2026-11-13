# A0-Q: Vertragsänderung für die Warteschlange und den Lernmodus (zur Freigabe, 13.11.)

Entwurf (nichts übernommen, nichts committet): `docs/egm/ha-ui/a0q_entwurf/ha-websocket-v1.md`, Unterschiede in `ha-websocket-v1.diff`. `docs/protocol/` ist unberührt. Box, MQTT-Vertrag und Datenmodell ändern sich **nicht**: HA nutzt die Meldung „unbekannter Tobie“, die es schon gibt. Version bleibt 1.

## 1. Was neu ist

- **„Später auflegen“:** Man legt am Handy vorab fest, was der **nächste neue Tobie** spielen soll, auf Box 1, Box 2 oder „egal welche“. Legt jemand danach einen unbekannten Tobie auf, ordnet HA ihn sofort zu. Kein Zeitlimit, die Seite muss nicht offen sein.
- Drei neue Befehle: `warteschlange/set` (vormerken), `warteschlange/list` (ansehen), `warteschlange/abbrechen`. Alle für jeden HA-Benutzer.
- Ein neues Ereignis „Warteschlange“ (angelegt, abgebrochen, abgearbeitet), damit die Seite die Meldung „Box 1: Der neue Tobie spielt jetzt …“ mit „Name geben“ zeigen kann.
- Zwei neue Fehler: „Es warten schon 5 Tobies“ und „Das wartet schon“. Höchstens 5 Vormerkungen, höchstens 30 Änderungen je Minute und Benutzer.
- Für „Rückgängig“ nach dem Zuordnen: ein kleines optionales Feld `als_neu` bei `zuordnung/remove`, damit die Karte „Neuer Tobie auf Box 1“ sofort wiederkommt.

## 2. Was sich ändert (nicht rückwärtskompatibel)

- **Der Lernmodus ist wieder nur für Administratoren** (`lernmodus/start`, `/antwort`, `/abbrechen`). Seit dem 12.11. durfte ihn jeder; ein normaler Benutzer bekommt jetzt „nicht erlaubt“. Im Alltag ersetzt ihn die Warteschlange.
- HA ordnet jetzt **von sich aus** zu, aber nur, wenn eine Vormerkung wartet. Ohne Vormerkung bleibt alles wie heute.

## 3. Lücken, die ich gefüllt habe (bitte mit freigeben)

- **Nur unbekannte Tobies.** Ein Tobie, der schon ein Ziel hat, wird nie umgehängt, der Eintrag bleibt stehen. Das prüft HA beim Schreiben selbst, auch wenn zwei Boxen denselben Tobie fast gleichzeitig melden: eine Zuordnung, ein Eintrag verbraucht.
- **Wer kommt zuerst.** Der älteste passende Eintrag. „Box 1“ und „egal welche“ stehen in einer Reihe nach Anlagezeit. Beispiel: erst „egal welche“, dann „Box 1“: der erste Tobie auf Box 1 nimmt „egal welche“.
- **Zweimal dieselbe Box:** erlaubt, der Reihe nach. Abgelehnt wird nur genau derselbe Eintrag (gleiche Box, gleiches Ziel).
- **Läuft gerade ein Lernmodus** auf der Box, rührt die Warteschlange diese Box nicht an. Die Einträge warten weiter.
- **Ziel inzwischen gelöscht:** HA wirft den Eintrag weg und probiert den nächsten; gibt es keinen, kommt die normale Karte „Neuer Tobie“.
- **Neustart von HA:** die Einträge bleiben, sie werden sofort gespeichert.
- **Absturz mittendrin:** Zuordnung und Austragen werden in einem Zug gespeichert, damit ein Eintrag nie zweimal gilt.
- **Protokoll ja, Mitteilung nein:** jede Vormerkung, jedes Abbrechen und jeder Treffer steht im Protokoll. Eine Mitteilung an Administratoren gibt es nicht, weil nichts verloren geht und „Rückgängig“ geht.
- **Kein Höchstalter** (Design: kein Zeitlimit). Die Seite kann zeigen, wie alt ein Eintrag ist und wer ihn angelegt hat.
- **Kleine Abweichungen vom Design:** „egal welche“ heißt im Vertrag `box = null` (ein Box-Name „alle“ wäre sonst möglich und würde kollidieren). Die Felder `automatisch_zugeordnet` und `ziel` kommen nicht an `neue_tobies/list`, sondern ins Ereignis „abgearbeitet“, weil ein so zugeordneter Tobie nie in dieser Liste steht. Beim gelöschten Ziel heißt der Grund `ziel_fehlt` (wie im Lernmodus), nicht `ziel_unbekannt`.

## 4. Fragen an Dich

Keine, die den Entwurf aufhält. Zwei Punkte, bei denen Du widersprechen kannst: (a) ohne `als_neu` käme die Karte nach „Rückgängig“ erst beim nächsten Auflegen zurück, mit dem Feld sofort; (b) ein liegengebliebener, nie zugeordneter Tobie kann einen Eintrag nehmen, wenn er vor dem gewünschten wieder aufgelegt wird. „Rückgängig“ und die Seite des Tobies bringen das in Ordnung.

---

## Anhang für den Koordinator: bestehende Tests und Code (nur Liste, nichts geändert)

**Tests, die nach der Übernahme anders erwarten** (Anpassung im Paket A9c, jede Änderung einzeln im Diff, wie bei A0 beschlossen):

- `homeassistant/tests/test_rechte_schutz.py`: Tabellenzeilen 18 bis 20 (`lernmodus/*`) von `alltag` auf `admin` (Nicht-Administrator bekommt `unauthorized`); Zeilen 47 bis 49 neu. `test_tabelle_enthaelt_jeden_befehl_der_vertragsuebersicht_genau_einmal` prüft `len(uebersicht) == 46` und liest den Vertrag live: **wird sofort rot, sobald der Entwurf nach `docs/protocol/` kommt**, solange die Tabelle nicht ergänzt ist (dann 49). `test_hello_sagt_nur_zu_was_gebaut_ist` (`f[-4:]`) ändert sich, sobald die neuen Fähigkeiten am Ende stehen.
- `homeassistant/tests/test_websocket_api.py`: in `ALLTAG_BEFEHLE` die drei `lernmodus/*`-Zeilen nach `ADMIN_BEFEHLE` (sonst scheitert `test_alltagsbefehle_sind_nicht_mehr_nur_fuer_administratoren`); `test_hello` (Fähigkeitenliste exakt); `test_subscribe_alle_themen_und_ungueltiges_thema` (7 Themen, wird 8 mit `warteschlange`).
- `homeassistant/tests/test_v11_erweiterungen.py`, Zeile 52: `f[-9:-4]` verschiebt sich um die Zahl der neu angehängten Fähigkeiten (zwei).
- `homeassistant/tests/test_texte.py`: kein Bruch, aber Pflicht: die zwei neuen Codes brauchen zugleich Eintrag in `fehler.py` (`HTTP_STATUS`), `strings.json` und `translations/de.json`.
- Frontend: `tests/frontend/texte.test.mjs` (jeder Code der Vertragstabelle braucht einen Text in `FEHLER`; Paket A5) und `tests/frontend/panel.test.mjs`, Zeile 66 (die zwei Codes in `NEU_FUER_NEUE_SEITE` aufnehmen, sonst verlangt der Test Texte in der alten Seite).
- Unverändert: `test_lernmodus.py` (ruft `hub.lernmodus` ohne Rechte), `test_services.py` (Aktionen waren schon admin), `test_mqtt.py` und `test_store.py` (ohne Vormerkung ändert sich nichts), `panel_quiet.test.mjs`.

**Was dem heutigen Code widerspricht:**

- `websocket_api.py`: `lernmodus/*` mit `recht="alltag"`; keine Befehle 47 bis 49; kein `als_neu`. `const.py`: `EREIGNIS_THEMEN` ohne `warteschlange`, `FAEHIGKEITEN` ohne die zwei neuen.
- `hub.py`, `neue_kennung`: kennt keine Vormerkung (heute: bekannt → `ack bekannt`, sonst Aufnahme und `ack neu`); `snapshot`, `hello.grenzen`.
- `store.py`: `_daten()` und `async_laden` kennen `warteschlange` nicht; „Zuordnung und Austragen in einem Schreibvorgang“ braucht eine kleine Erweiterung von `async_aendere` (der Mutator ändert heute nur die Konfiguration).
- `schutz.py`: neue Menge „warteschlange“. `lernmodus.py`: nichts am Ablauf, `offener_vorgang(box)` genügt für „lebender Vorgang“.
- `mqtt.py`: keine Änderung. `_on_unknown` reicht an `neue_kennung` weiter, `sende_ack(… "bekannt")` gibt es schon; **die Box muss nichts Neues melden.**
