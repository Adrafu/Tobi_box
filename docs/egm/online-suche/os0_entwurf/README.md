# Online-Suche, Paket OS0: Entwurf der Vertragsänderungen

Stand 18.11. Grundlage: `docs/designs/online-suche.md` (Rev. 2.3, Abschnitt 9) und `docs/egm/online-suche/resolve.md`.
**Von Tobias freigegeben am 18.11.** („Ja, freigeben“) und in `docs/protocol/ha-websocket-v1.md` und `docs/data-model.md` übernommen. Die Diffs zeigen den Stand vor der Übernahme.

| Datei | Inhalt |
|---|---|
| `ha-websocket-v1.md` | volle Kopie von Vertrag W mit den Änderungen |
| `ha-websocket-v1.diff` | `diff -u docs/protocol/ha-websocket-v1.md docs/egm/online-suche/os0_entwurf/ha-websocket-v1.md` |
| `data-model.md` | volle Kopie des Datenmodells mit den Änderungen |
| `data-model.diff` | `diff -u docs/data-model.md docs/egm/online-suche/os0_entwurf/data-model.md` |

`mqtt-v1.md` bleibt unverändert (Design 9.4); der Kopf-Eintrag sagt es. Die Option `online_ki_entitaet` der Integration steht nur als ein
Satz im Kopf-Eintrag und in 3.15 (nicht Teil von Vertrag W). Die Version bleibt 1, alles additiv, mit den im Kopf-Eintrag genannten Ausnahmen
(neuer Wert `online` in `cover_quelle` und `art_quelle`; Rückfall auf eine ältere Integration macht `manuell` daraus).

## Was geändert ist

**Vertrag W (`ha-websocket-v1.md`)**

| Stelle | Änderung | Design |
|---|---|---|
| Kopf | Eintrag „Änderung 18.11. (Online-Suche, Paket OS0 …)“, Ausnahmen, Status-Zeile | 9, 9.2 |
| 2.1, 2.3 | Rechte: 57 bis 63 admin, 64 lesen; HTTP-Vorschau und `DELETE …quelle=online` admin; Absatz „Online-Suche“ (R1); MQTT „nichts“ | 9.2, R1 |
| Übersicht 3 | Zeilen 57 bis 64 (56 war die letzte vergebene Nummer, keine Verschiebung nötig) | 9.2 |
| 3 (Serie-Kurzform), 14.2 | Felder `online` (alle), `online_vorschlaege` (nur Administratoren, nur `serien/list`, `serie/get`, Nr. 51); `cover_quelle`/`art_quelle` mit `online`; Filterwert `online_vorschlag` | 9.2, R1 |
| 1 `hello`, 2 `subscribe` | Fähigkeit `online_suche`; Thema `online` (für Nicht-Administratoren still gestrichen) | 9.2, 9.3 |
| 3.2 `serie/get` | Folge: `beschreibung` (höchstens 300), `beschreibung_gekuerzt`, `alter_ab`, `beschreibung_quelle`; für Administratoren `online_vorschlaege_liste` | 9.2, R4 |
| 3.15 (neu) | Befehle 57 bis 64 mit Eingabe, Ausgabe, Fehlern, Recht, Idempotenz, MQTT; Begriffe (Feldnamen, Quellen, Treffer, Vorschlag mit Quelle `claude` und `grund`); HTTP-Vorschau; Grenzen; `quellen.claude` in Nr. 63; keine Vorschläge zum Verschieben | 9.2, 3.4, 4.8 |
| 3.12 Nr. 44 | berührt auch `cover-online.jpg` nie | 7.2 |
| 4, 4.11 (neu) | Thema `online` (nur Administratoren): `snapshot`, `stand` (gebündelt 2 s), `fertig`, `quelle` | 9.3 |
| 7 | 6 neue Fehlercodes mit HTTP-Nummern; Befehle bei `serie_nicht_gefunden`, `folge_nicht_gefunden` ergänzt | 9.2 |
| 9 | Ausnahme-Eintrag zu den neuen Werten `online` | 9.2 (GB-11) |
| 14.1 | Zeile `online_suche` | 9.2 |
| 14.3 | Online-Cover, Vorrang eigen > online > auto, `DELETE …?quelle=online` | 6.4, 7.2 |

**Datenmodell (`data-model.md`)**

| Stelle | Änderung | Design |
|---|---|---|
| Kopf | Eintrag „Änderung 18.11. …“, Zeile „Gilt für“ | 9.1 Punkt 5 |
| 1.6 | Zeilen `cover-online.jpg`, `tobibox.online`, `tonies.json` | 9.1 Punkt 5 |
| 5 | `art_quelle` mit `"online"` (die Stelle `data-model.md:544` laut Checkliste G2-11; Rückfall `manuell`); reservierter Dateiname `cover-online.jpg`, Vorrang eigen > online > auto; Zusammenführen kopiert auch das Online-Cover; Sync nimmt es mit `cover*.jpg` schon aus | 9.1 Punkt 1, 2; 7.2 |
| 5b (neu) | Store `tobibox.online`: Tabelle der Schlüssel, Version 1 / `minor_version` 1, Speichern, Verfall, Pflegestellen, nicht gesynct, in der HA-Sicherung | 9.1 Punkt 3; 7.3 |
| 13 (neu) | `<config>/tobibox/tonies.json`: Zwischenspeicher, darf fehlen, abgelegte Felder | 9.1 Punkt 4; 3.1, 7.4 |

Die Checkliste G2-11 (`art_quelle = online`) deckt sich so: `data-model.md:544` (jetzt in 5), Vertrag W 14.2 (Tabelle), `const.py:113`
`ART_QUELLEN` (Code, später in OS3).

## Vorschlag Entwurf (das Design schweigt oder ist unklar; ich habe das Naheliegende festgelegt)

1. **Liste der Vorschläge lesen.** Das Design nennt nur den Zähler `online_vorschlaege`, aber die Karte „bitte ansehen“ braucht Quelle, Feld,
   Name und `grund`. Vorschlag: Administratoren bekommen in `serie/get` das Feld `online_vorschlaege_liste`; Nr. 58 nimmt zusätzlich `serie_id` + `vorschlag_id`
   statt `treffer_id`, damit „Ansehen“ dieselbe Übersicht zeigt.
2. **Namensvorschlag übernehmen.** Design 5.4 sagt „wirkt wie `serie/rename`“. Vorschlag: Die Seite ruft Nr. 59 mit `vorschlag_id` und `felder: ["serie_name"]`
   (mit `stand`); HA macht daraus ein Umbenennen von Hand (Namensprüfung, `name_ungueltig`). Die Seite kann alternativ `serie/rename` rufen; dann bleibt der Vorschlag stehen.
3. **Feldnamen.** `serie_name`, `art`, `cover` gelten für den Eintrag, `folge_titel`, `nummer`, `beschreibung`, `alter_ab` je Folge als `<feld>@<folge>`
   (so lesbar aus 6.3 und den Schlüsseln `hand` und `zurueckgenommen`). Trennung am ersten `@`.
4. **Quellenschlüssel.** Nr. 57 `quellen`: `itunes`, `tonies`. Nr. 63 `quellen`: `itunes`, `tonies`, `tonies_shop`, dazu `claude`. `quellen.claude` ist
   `{"eingerichtet": bool, "erreichbar": bool}` (gleiche Form wie die anderen Quellen; **Festlegung PL** 18.11. statt `zustand`).
5. **`treffer_id`:** 16 Zeichen `[0-9a-f]`. **Vorschau-Fehler:** 410 bei Ablauf, 404 `cover_nicht_gefunden` ohne Bild.
6. **Nr. 58 Werte.** `heute`/`neu` sind die Werte (string, int, `null`); bei `cover`: `heute` = Cover-Quelle, `neu` = `true` (das Bild kommt über die Vorschau).
   `sicher` und `hand` je Feld, gleiche Werte fehlen, `grund` nur bei Claude. Lädt ein Treffer ab Platz 6 das Bild nach (Design 8.2), kann das Netz brauchen; schlägt es
   fehl, fehlt `cover` (kein neuer Fehlercode).
7. **Nr. 59.** `anfrage_id` optional (wie 2.2); `felder` mindestens 1; der Vorschlag verschwindet, wenn alle seine Felder übernommen sind (kein `verworfen`);
   Fehler zusätzlich `name_ungueltig`, `medien_nicht_erreichbar`, `medien_schreibfehler` (die Fehlerliste des Designs nennt sie nicht, die Schreibwege brauchen sie).
8. **Nr. 60.** `zurueckgenommen` ist die Zahl der Felder; `serie_nicht_gefunden`, `invalid_format` und `medien_*` ergänzt; zweiter Aufruf setzt 0 Felder zurück.
   Im Store bekommt eine zurückgenommene Änderung den Status `zurueckgenommen` (und zählt nicht mehr für `online`). Das Design nennt nur `offen` und `fertig`.
9. **Nr. 61.** Zweites „Nein“ gibt `vorschlag_nicht_gefunden`; `serie_nicht_gefunden`, `invalid_format` ergänzt.
10. **Nr. 62.** Ausgabe `{"lauf": <wie Nr. 63> | null}`. **Nr. 63:** `lauf` ist nur ein laufender Lauf (`laeuft`, `pausiert`, `angehalten`); beendete Läufe
    (`fertig`, `angehalten`, `abgebrochen`) stehen in `letzte_laeufe` mit `zahlen` = `{erledigt, gesamt, geaendert, vorschlaege, keiner}`. `tonie_liste.stand` ist ein Zeitstempel.
11. **Nr. 64.** Ohne Beschreibung `beschreibung` und `quelle` = `null` (kein Fehler); bei Quelle `tonies_shop` auch `alter_ab`.
12. **Nr. 57.** Überraschungs-Serie: `invalid_format`; Treffer „beste zuerst“; `art` und `nummer` und `tracks` fehlen, wenn unbekannt.
13. **Feld `online` der Kurzform:** `null`, wenn keine Änderung jünger als 30 Tage; `felder` ohne `@<folge>` und ohne Doppelte. **Filter `online_vorschlag`**
    von einem Nicht-Administrator: `unauthorized`. `DELETE …?quelle=online`: ohne Online-Cover kein Fehler (wie bei `quelle=eigen`), anderer `quelle`-Wert `invalid_format`.
14. **Ereignis `online`:** `stand` und `fertig` tragen `vorgang` (`lauf` oder `zuruecknahme`); Zahlen der Rücknahme `zurueckgenommen`, `uebersprungen_anzahl`;
    `quelle` nur für `itunes`, `tonies`, `tonies_shop` (Claude hat kein Ereignis). `snapshot` ist die Ausgabe von Nr. 63.
15. **Konstanten** (Tabelle am Ende von 3.15) tragen Namensvorschläge; Werte nur aus dem Design.
16. **`tonies.json`:** Kopf `schema_version`, `geladen_am`, `etag`, dazu `eintraege`; `tracks` als Liste der Titel; Typen der Felder wie in der Quelle (`release` als Text).
    **Store:** `folgen.<f>.seite` und `gewaehlt` sind ohne Erklärung im Design; ich habe `gewaehlt` als „von Hand gewählt“ gedeutet und `seite` nur genannt.
17. **Mengenregeln (2.4):** keine neuen. Alle Befehle außer Nr. 64 sind admin; die Drossel gegen die Quellen steht im Design 8.2 und nicht im Vertrag.
18. **Zusammenführen:** Das Ziel ohne eigenes Cover übernimmt auch das Online-Cover der Quelle (Design 7.2). Ob ein eigenes Cover der Quelle vor dem Online-Cover der Quelle geht, steht dort nicht; Datenmodell lässt es bei „das Cover der Quelle“.

## Die 4 Punkte (PL, Design 13), die Tobias mit der Freigabe bestätigt

1. Claude nur für Einträge mit Grund (neu einsortiert oder `serie_aus_*`); Entität als Option der Integration, **gleich eingeschaltet** (Tobias 18.11.; Vorgabe: die `ai_task`-Entität der Claude-Integration (`anthropic`), wenn es genau eine gibt; abschaltbar) (Vertrag: `quellen.claude`).
2. `serie_aus_interpret` / `serie_aus_ordner` löst die Online-Suche nie auf (kein Vertragstext nötig; wirkt im Verhalten, Design 5.5).
3. Keine Vorschläge zum Verschieben (Vertrag: Vorschlagsarten nur `felder` und `zusammenfuehren`).
4. Die Quelle der Namensvorschläge heißt auf der Seite „Claude“ (Vertrag: Quelle `claude`).

## Unklarheiten im Design für die Projektleitung

* Punkt 1 oben (Vorschläge lesen) ist eine echte Lücke: Ohne `online_vorschlaege_liste` und die Erweiterung von Nr. 58 kann die Karte „bitte ansehen“ nicht gebaut werden.
  Alternative wäre ein neuer Befehl 65; ich habe das vermieden, weil das Design „57 bis 64“ nennt.
* Punkt 2 (Namensvorschlag über Nr. 59 oder `serie/rename`) und Punkt 8 (Status einer zurückgenommenen Änderung) sollten bestätigt werden.
* Nr. 58 ist laut Design ohne Netz-Fehler; das Nachladen von Bildern jenseits Platz 5 braucht aber Netz (Design 8.2).
* Ob Online-Änderungen den `stand` der Serie ändern, sagt das Design nicht ausdrücklich; es ergibt sich aus 3 („`stand` rechnet über `name`, `folgen`, `anzeige`, `nummer` …“): Namen, Titel, Nummer und `pruefen` ändern ihn, Beschreibung, Alter, Cover und Art nicht.

## Festlegungen der Projektleitung zu den Unklarheiten (18.11.)

- Vorschläge lesen über `online_vorschlaege_liste` in `serie/get` (nur Administratoren) und Nr. 58 mit `serie_id` + `vorschlag_id`: **angenommen**
  (Lücke im Design, ohne neuen Befehl; Design 9.2 ergänzt).
- Namensvorschlag übernehmen über Nr. 59 (`vorschlag_id`, `felder: ["serie_name"]`, `stand`), wirkt wie ein Umbenennen von Hand: **angenommen**.
- Status `zurueckgenommen` einer Änderung im Store: **angenommen**.
- `quellen.claude` = `{"eingerichtet", "erreichbar"}`: **geändert** (statt `zustand`).
- Nr. 58 ohne eigenen Netzfehler, nachgeladenes Bild fehlt bei Fehler: **angenommen**.
- Zusammenführen: Vorrang eigen > online > auto gilt auch beim Kopieren der Quelle: **angenommen** (wie heute zuerst `cover-eigen.jpg`).
- Alle übrigen Punkte „Vorschlag Entwurf“ 1–18: **angenommen**.

## Goldfisch OS0, Runde 5 (`../review_goldfisch_os0.md`, `../resolve.md` Runde 5) eingearbeitet

Design jetzt Rev. 2.4. Im Vertragsentwurf geändert:

| Befund | Wo |
|---|---|
| GO-1 | Store `vorschlaege` mit `werte` (Cover: `cover_url`, `collection_id`; Claude: `serie_name`) und `name_vorher` (data-model 5b); Nr. 58 mit Vorschlag baut aus dem Store und lädt das Cover-Bild neu (Netz), Nr. 59 nimmt Werte aus dem Store (W 3.15) |
| GO-2 | Store `serien.<id>.marke.claude` `{ergebnis: vorschlag\|behalten\|fehler\|aus, zeit}` (data-model 5b) |
| GO-3 | Nr. 59: `stand` Pflicht bei `serie_name`; Vorschlag fällt weg, wenn der Name nicht mehr `name_vorher` ist |
| GO-4 | Schema der Claude-Antwort ohne `sicher`: `os0_entwurf/claude_anweisung.md` (kein Vertragstext) |
| GO-10, GO-11 | `quellen.claude` = `{eingerichtet, erreichbar}` (schon so) |
| GO-12 | `grund` (`angehalten`, `neustart`, `quelle`) in `letzte_laeufe` und Ereignis `fertig`; laufender Zustand `wird_angehalten` |
| GO-13 | `subscribe`: erst auflösen, dann `online` streichen, leere Menge bleibt leer; Rolle gilt bis zum neuen Abo (W 4.11, 2, Kopf) |
| GO-14 | Nr. 62 „Endzustand ja“; `felder` Obergrenze × 4 + 3; `invalid_format` bei der Überraschungs-Serie bleibt; ein angenommener Claude-Name ist keine Online-Änderung (`aenderung_id` `null`, nicht in `online.felder`) |
| GO-15 | `gewaehlt` entfällt, `seite` = Pfad der Shopseite (data-model 5b) |
| GO-17 | Zusammenführen kopiert die Datei, die die Quelle anzeigt (eigen vor online), unter ihrem Namen; `hand.cover` und `zurueckgenommen.cover` ziehen mit (data-model 5) |
| GO-8 | kein Schnappschuss für den Namen (data-model 5b) |

Die Punkte „Vorschlag Entwurf“ 1 bis 18 oben gelten weiter, soweit hier nicht anders gesagt (Punkt 4: `quellen.claude`; Punkt 7: `felder` Obergrenze).
