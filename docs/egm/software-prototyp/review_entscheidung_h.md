# Review Entscheidung H (Commit 4266de4): Lernmodus wartet still

Prüfer ohne Vorwissen. Geprüft: `git show 4266de4`, `CLAUDE.md`, `docs/designs/box-software.md`
(Entscheidung H, Sitzungstabelle, Tabelle „Lernmodus“, CUJ 7a/7b), `docs/protocol/core-interface.md`
(9.8, Punkt 29, 3.4, 7), `docs/protocol/mqtt-v1.md` 4.1 und 4.2, `box/src/tobibox/session.py`, `app.py`,
`learn.py`, `core.py`, `outbox.py`, `ha_ersatz.py`, `lauf.py` und die neuen Tests.

Stand der Tests vor der Prüfung: `pytest -q tests/unit tests/cuj` in `box/`: 1436 grün.
Wegwerf-Tests lagen nur in `.../scratchpad/rvH/test_rv.py` (nicht im Repo).

Gesamteindruck: Die Regel ist sauber umgesetzt. Der Teilautomat `session` bleibt rein
(`step(zustand, ereignis, jetzt)`, Fristen nur auf `jetzt.mono`, keine Uhr, kein Zufall). Die Box kann nicht
länger als 10 s im Warten hängen (Frist über `Takt`, Abheben und anderer Tobie lösen es auch). Es gibt aber
einen echten Fehler (Befund 1) und zwei Lücken im Vertrag (Befund 2 und 3).

---

## Befund 1 — Mittel — Jede Konfiguration beendet das Warten eines bekannten Tobies oder einer Aktionskarte

*   **Stelle:** `box/src/tobibox/session.py` Zeile 714 bis 722 (`_konfig`, Bedingung
    `f.uid in e.konfig.zuordnungen`); Vertragstext `docs/protocol/core-interface.md` 9.8, Ende-Punkt 1
    („`KonfigGeladen`, deren `zuordnungen` die Kennung des wartenden Tobies enthalten“); Tabellenzeile in
    `docs/designs/box-software.md` Zeile 1034.
*   **Szenario:** Tobias lernt einen schon zugeordneten Tobie neu an (HA fragt vor dem Überschreiben nach,
    `mqtt-v1.md` 4.2 Punkt 4). Während die Box wartet, kommt irgendeine neue Konfiguration von HA (anderer
    Tobie geändert, Revision + 1, Sync). Die Kennung des wartenden Tobies steht in jeder Konfiguration, weil
    er ja schon zugeordnet ist. Das Warten endet sofort und der **alte** Tobie spielt sein altes Ziel. Genau
    das soll Entscheidung H verhindern („Ein Druck soll nicht die Überraschung oder das alte Ziel starten,
    solange HA noch antworten kann“). Bei einer wartenden Aktionskarte (Gute Nacht) löst dieselbe fremde
    Konfiguration die Aktion aus.
*   **Beleg:** Wegwerf-Test (`rvH/test_rv.py`): `wartet(UID_S1)`, dann `KonfigGeladen` mit unveränderten
    `ZUORDNUNGEN`, Revision 9. Ergebnis: `Abspielen(serie_id='s1', ...)`, Zustand `spielt`. Mit `UID_NACHT`:
    `AktionAusgeloest('gute_nacht')`. Die Unit-Tests prüfen nur „Konfiguration ohne diesen Tobie“ (unbekannter
    Tobie, `test_konfig_ohne_diesen_tobie_laesst_das_warten_weiterlaufen`) und „neue Zuordnung für bekannten
    Tobie“ (Ziel ändert sich). Der Fall „Konfiguration mit unverändertem Ziel“ fehlt.
*   **Vorschlag:** Beim Beginn des Wartens das Ziel merken, das der Tobie dann hatte (Feld im Zustand, z. B.
    `lern_ziel`: `None` für unbekannt, sonst `Zuordnung`). Das Warten endet nur, wenn die neue Konfiguration
    für diese Kennung ein **anderes** Ziel enthält (bei unbekanntem Tobie: überhaupt eines). Vertrag 9.8 und
    Sitzungstabelle entsprechend anpassen und zwei Tests ergänzen (gleiche Konfiguration, fremde Revision).

## Befund 2 — Mittel — 10 s sind kürzer als die Rückfrage von HA beim Überschreiben

*   **Stelle:** `docs/protocol/mqtt-v1.md` 4.2 Punkt 4 (HA fragt vor dem Überschreiben nach) gegen
    `LERN_ANTWORT_FRIST_S = 10` (`session.py` Zeile 31) und Entscheidung H2.
*   **Szenario:** Bekannter Tobie wird neu angelernt. HA fragt Tobias „Wirklich überschreiben?“. Das dauert
    länger als 10 s. Nach 10 s spielt die Box das alte Ziel, danach wechselt sie bei „Ja“ auf das neue. Für
    unbekannte Tobies ist das kein Problem (kein Rückfrage-Fall), für bekannte schon. Der Vertrag sagt das
    nirgends offen; er stellt die 10 s als „HA antwortet in dieser Zeit“ dar.
*   **Beleg:** Das Design nennt die Rückfrage in CUJ 7b ausdrücklich, 9.8 Punkt 3 behandelt nur „Frist
    abgelaufen“. Kein Test und kein Vertragssatz zur Rückfrage.
*   **Vorschlag:** Entweder festhalten, dass bei einem bekannten Tobie das Spielen des alten Ziels nach 10 s
    gewollt ist (Tobias entscheiden lassen), oder HA schickt bei einer Rückfrage sofort einen `ack` mit eigenem
    `grund` (z. B. `rueckfrage`), der das Warten **verlängert** (neuer Endpunkt, einmal). Mindestens in
    `mqtt-v1.md` 4.2 und im Plan als offene Frage eintragen.

## Befund 3 — Mittel — Nach „abgelehnt“ spielt die Überraschung, aber der Eintrag in `unknown.json` ist weg

*   **Stelle:** `box/src/tobibox/app.py` Zeile 127 (Outbox löscht zuerst) und `session.py` Zeile 358
    (`melden=False`); Vertrag `core-interface.md` 9.8 Ende-Punkt 2 („ohne ein zweites `Melden`“) und
    `mqtt-v1.md` 4.2 („der `ack` löscht den Eintrag wie bisher“).
*   **Szenario:** Unbekannter Tobie im Lernmodus, HA antwortet `abgelehnt` (z. B. HA kennt den Lernlauf nicht
    mehr, `kein_lernziel` im HA-Ersatz). Die Outbox löscht den Eintrag. Die Sitzung beendet das Warten und
    spielt die Überraschung mit Ton `unbekannt`, meldet aber nicht erneut. Ergebnis: Der Tobie liegt als
    „unbekannt“ auf der Box, `unknown.json` ist leer, HA hat keinen „neuer Tobie“. Er taucht erst auf, wenn
    das Kind ihn abhebt und neu auflegt. Das widerspricht dem Satz aus CUJ 7a / `mqtt-v1.md` 4.1 Schritt 1
    („jede Überraschung wegen eines unbekannten Tobies hat einen offenen Eintrag“). Beim Fristablauf ist es
    anders und in Ordnung: Der Eintrag bleibt als `gelernt` offen und wird erneut veröffentlicht.
*   **Beleg:** `test_cuj07b_app.py::test_abgelehnt_aus_der_verdrahtung_...` prüft ausdrücklich
    `dienst.unknown() == {}` neben der laufenden Überraschung; der bestehende CUJ-Test
    `test_ohne_lernziel_lehnt_der_ha_ersatz_ab_der_eintrag_ist_trotzdem_weg` ebenso. Beide halten den Zustand
    für richtig.
*   **Vorschlag:** Nur beim Ende durch `abgelehnt` und nur für einen unbekannten Tobie `Melden("unbekannt")`
    erneut ausgeben (`melden=True`). Die Reihenfolge in `app.py` (Outbox zuerst, dann Kern) sorgt dafür, dass
    der neue Eintrag nach dem Löschen entsteht. Beim Fristablauf weiter `melden=False`. Alternativ im Vertrag
    festschreiben, dass das gewollt ist, und HA bei `abgelehnt` für einen unbekannten Tobie `grund="neu"`
    senden lassen. Test ergänzen.

## Befund 4 — Niedrig — Jede „gelernt“-Bestätigung erreicht den Kern, auch eine, die die Outbox verwirft

*   **Stelle:** `app.py` Zeile 127 bis 129 (der Rückgabewert von `ausgang.bestaetigt` wird ignoriert);
    `session.py` Zeile 362 bis 367 (`_bestaetigt` prüft nur Kennung, `art`, `grund`, nicht `zuletzt`).
*   **Szenario:** `mqtt-v1.md` 4.1 Punkt 4 sagt, dass HA nach einem Absturz „erneut bestätigt (idempotent)“.
    Trifft ein später eintreffendes, altes `ack` mit `grund="abgelehnt"` und `art="gelernt"` für **dieselbe**
    Kennung ein, während die Box in einem neuen Lernlauf wartet, endet das Warten zu früh. Die Outbox
    erkennt das Ack als veraltet (`ack_veraltet`, wirkungslos), die Sitzung nicht.
*   **Beleg:** Code. `outbox.bestaetigt` liefert `False`, `app.verarbeite` ignoriert den Wert.
*   **Vorschlag:** In `app.py` nur dann an den Kern geben, wenn die Outbox die Bestätigung angenommen hat
    (`True`), oder `zuletzt` mitgeben und im Vertrag 3.4 dazu schreiben. Test: veraltetes `abgelehnt` beendet
    das Warten nicht.

## Befund 5 — Niedrig — Aktionskarte löst nach Fristablauf von selbst die Aktion aus

*   **Stelle:** `core-interface.md` 9.8 („sie löst dann keine Aktion aus“) und Ende-Punkt 3 (Frist: „Wirkung
    wie bei der Ablehnung“); `session.py` Zeile 268 (`_auflegen` mit `warten=False` feuert `AktionAusgeloest`).
*   **Szenario:** Das Kind legt im Lernmodus die Gute-Nacht-Karte auf. 10 s später (ohne jede Eingabe) beginnt
    Gute Nacht, die Lautstärkegrenze greift. Der Vertrag erwähnt das nicht; getestet ist nur der Weg über
    „abgelehnt“ (`test_abgelehnt_aktionskarte_loest_dann_die_aktion_aus`), nicht die Frist.
*   **Vorschlag:** Entscheiden (Tobias): Aktionskarten im Lernmodus gar nicht warten lassen und die Aktion
    nie auslösen, oder den Fall im Vertrag und mit einem Frist-Test festhalten. Wirkt zusammen mit Befund 1.

## Befund 6 — Niedrig — Vertrag und Code weichen bei „dieselbe Kennung“ ab

*   **Stelle:** `core-interface.md` 3.x Zeile 237 (`LernenGeaendert`: „ein `Aufgelegt` mit Kennung, das bei
    `aktiv=True` eintrifft, wird nicht gespielt, sondern abgewartet“) und Sitzungstabelle Zeile 1031 gegen
    `session.py` Zeile 389 (Zustand `spielt`, gleiche Kennung, neue Vorgangs-ID: nichts, 9.4).
*   **Szenario:** Tobie A spielt, ein `REMOVED` ging verloren, A wird mit neuer Vorgangs-ID gemeldet,
    der Lernmodus läuft. `learn` beendet den Lernmodus (Ton `lernen_ende`, `gelernt` gemeldet), die Sitzung
    wartet nicht und spielt einfach weiter. Das ist vernünftig (9.4), steht aber nicht in 9.8. Zweitens
    nennt die Sitzungstabelle den Zustand `unbekannt` (Leser unterbrochen) nicht; der Code behandelt ihn
    richtig (Pause, Zeiger speichern, dann Warten).
*   **Beleg:** Wegwerf-Test: `lernt("spielt")`, `A(UID_S1, "v9")`: Ausgabe `[]`, Zustand `spielt`,
    `lern_wartet_bis` ist `None`.
*   **Vorschlag:** Zwei Sätze in 9.8 und eine Zeile für `unbekannt` in der Tabelle; ein Test für den
    `spielt`-Fall.

## Befund 7 — Niedrig — Reihenfolge in `mqtt-v1.md` 4.2 widerspricht der eigenen Empfehlung

*   **Stelle:** `mqtt-v1.md` 4.2 Punkte 4 und 5 (erst `ack`, dann Konfiguration) gegen den Absatz
    „HA soll die Konfiguration vor oder gleichzeitig mit dem `ack` veröffentlichen“.
*   **Folge:** Kommt der `ack` `zugeordnet` zuerst und die Konfiguration später als 10 s, löscht der `ack` den
    Eintrag, die Box spielt nach 10 s die Überraschung mit Ton `unbekannt` und wechselt erst danach auf das
    Ziel. Kein Hängen, kein Verlust (die Sitzung ignoriert `zugeordnet` richtig), aber hörbar.
*   **Vorschlag:** Punkte 4 und 5 tauschen oder den Hinweis in die Schritte schreiben.

## Befund 8 — Niedrig — Tests: ein Test prüft weniger als sein Name, Lücken

*   `box/tests/cuj/test_cuj07b_app.py` Zeile 253, `test_bestaetigung_fuer_gelernte_geht_auch_an_den_kern`:
    Prüft nur `dienst.app.kern is not vorher`. `core.step` liefert aber **immer** ein neues `KernZustand`.
    Der Test würde auch grün bleiben, wenn die Sitzung die Bestätigung ignoriert. Besser: Zustand
    `lern_wartet_bis` vorher gesetzt, nachher `None`.
*   `box/tests/unit/test_session_lernwarten.py` Zeile 300,
    `test_dienst_neustart_marker_bleibt_waehrend_des_wartens_der_tobie`: Prüft nur, dass `figur.uid` gesetzt
    ist. Weder `lauf.json` noch das Verhalten nach dem Neustart (Tobie bleibt `pausiert`, startet nicht) noch
    ein `DienstEndet` im Warten sind getestet.
*   Fehlende Fälle: Konfiguration mit unverändertem Ziel (Befund 1); veraltetes `abgelehnt` (Befund 4);
    Aktionskarte und Frist (Befund 5); `spielt` mit gleicher Kennung (Befund 6); Leserausfall im Warten
    (`LeserHallo`/`LeserAlarm`, danach `LeserHerzschlag(present=False)` beendet das Warten); Warten
    beginnt im Zustand `unbekannt`; `Gesperrt` und ein anderer Tobie **ohne** vorheriges `LernenGeaendert(False)`;
    `StummBeginnt`/`StummEndet` während des Wartens; erneuter `HaLernmodus` während des Wartens.
    (Die Fälle laufen nach Lesen des Codes vermutlich richtig, sind aber nicht abgesichert.)

---

## Geprüft, ohne Befund

*   **Teilautomat rein:** `session.step` bleibt `step(zustand, ereignis, jetzt)`; die neuen Funktionen lesen
    nur `jetzt.mono`; kein Import von Uhr, Datei oder Zufall. `LERN_ANTWORT_FRIST_S` läuft auf `mono`
    (Test mit Wanduhr-Sprung vorhanden).
*   **Code gegen Vertrag:** Reihenfolge `session` vor `learn` (`core.py` `TEILAUTOMATEN`) stimmt mit 9.8 und
    der `LernenGeaendert`-Zeile überein. Frist, Abheben (auch per Herzschlag), Hauptknopf, Vor, Zurück,
    Lautstärke, `Gesperrt`, Wiedermeldung und gleiche Kennung mit neuer Vorgangs-ID im Warten verhalten sich
    wie beschrieben. `Hauptknopf lang` bleibt bei `idle`.
*   **Hängen:** Das Warten endet spätestens nach 10 s über `Takt` (100 ms). Abheben, anderer Tobie,
    `Gesperrt` und `abgelehnt` räumen `lern_wartet_bis` ebenfalls auf (`_auflegen` setzt es als Erstes auf
    `None`). Kein Pfad lässt den Zustand `pausiert` mit gesetzter Frist ohne Ausgang zurück.
*   **Selbstständiges Spielen:** Hauptknopf, Vor, Zurück starten nichts. `ack` `zugeordnet`/`neu`, Art
    `unbekannt` und `abgelehnt` für eine andere Kennung beenden das Warten nicht. Die Zuordnung für einen
    anderen **unbekannten** Tobie lässt das Warten weiterlaufen.
*   **`ack` zuerst, Konfiguration danach:** Sitzung ignoriert `zugeordnet`; Konfiguration innerhalb von 10 s
    startet das Ziel ohne Ton; später: Überraschung, dann Wechsel nach 9.14. Kein Hängen.
*   **Sitzungstabelle und Entscheidung G:** Dienst-Neustart im Warten: Der Marker `lauf.json` folgt
    `session.figur` (liegt im Warten), der Tobie bleibt danach `pausiert`; der Lernmodus überlebt den Neustart
    nicht. Keine Kollision mit `neustart_uid` (wird erst im normalen Zweig von `_auflegen` verbraucht).
*   **Regel 6.2.2 „stumm“:** `lernen_ende` wird unter „stumm“ zum Hinweiston (Kernregel); Ende des Wartens
    unter „stumm“ ergibt `gehalten` plus Hinweiston (getestet).
*   **Regel 6.2.4 (doppelte Meldungen) und `unknown.json`:** `Melden("unbekannt")` aus der Sitzung und
    `Melden("gelernt")` aus `learn` im selben Schritt: `gelernt` gewinnt, die Outbox kennt den Fall
    (`gelernt` ersetzt `unbekannt`, nicht umgekehrt). Beim Fristablauf bleibt der Eintrag offen.
*   **Vorgangs-ID-Regeln 9.1 bis 9.4:** Nach dem Ende des Wartens bleibt die Vorgangs-ID des Tobies; eine
    Wiedermeldung ist weiter ein No-op. Gleiche Kennung mit neuer ID im Warten ändert nur die ID.
*   **CUJ 7a, 7b, 20:** 7a gilt ohne Lernmodus unverändert (Satz „spielt sofort“ stimmt dort weiter). 7b ist
    im Design eingearbeitet. 20 (Start mit liegendem Tobie) berührt den Lernmodus nicht.
*   **Gute-Nacht-Logik:** `GuteNachtEnde` und `Gute-Nacht-Grenze` wirken im Warten nicht (nichts läuft);
    nach dem Warten gilt die Grenze wie bei jedem Auflegen. (`bedtime.py` ist im Kern noch nicht eingetragen,
    nur gegen den Vertragstext geprüft.)
*   **`learn.py`:** Nur Docstring geändert; Verhalten unverändert (Test `test_aufgelegt_gibt_nur_den_endeton...`
    stimmt).
*   **Plan, Mac-Anleitung:** Rev. 3.10 und die Anleitung stimmen mit dem Vertrag überein (keine veralteten
    Sätze wie „startet weiter die Überraschungs-Serie“ mehr im Repo außerhalb der Review-Ordner).

---

## Auflösung (07.11., nach entschiedener Projektleitung)

1.  **Behoben.** Die Sitzung merkt sich beim Beginn des Wartens das Ziel des Tobies (`lern_ziel`, unbekannt: keins). Nur ein anderes Ziel für diesen Tobie beendet das Warten, bei einem unbekannten Tobie jedes. Vertrag 9.8, Punkt 29, Design-Tabelle angepasst. Tests: gleiche Konfiguration, fremder Tobie geändert, Aktionskarte, entferntes Ziel, andere Aktion, über die echte `App`.
2.  **Als gewollt festgehalten**, kein neuer Mechanismus: 9.8 (Ende 3), Punkt 29, `mqtt-v1.md` 4.2, Design (H2, CUJ 7b), Plan.
3.  **Behoben.** Nach „abgelehnt“ meldet die Sitzung einen unbekannten Tobie erneut als `unbekannt` (`unknown.json` hat ihn wieder); bei einem bekannten Tobie und beim Fristablauf kein `Melden`. Tests: Unit, Kern, `SimBox` und echte `App` mit `unknown.json`.
4.  **Behoben.** `app.py` gibt `Bestaetigt(art="gelernt")` nur an den Kern, wenn die Outbox sie angenommen hat (auch im Testaufbau `SimBox`). Tests: veraltetes `zuletzt`, doppeltes Ack im neuen Lernlauf, fremde Kennung ohne Eintrag.
5.  **Festgehalten und getestet.** Nach der Frist löst eine Aktionskarte ihre Aktion aus (9.8, Punkt 29, Design); Unit-Test für `gute_nacht` und `status` über die Frist.
6.  **Vertrag nachgezogen.** 9.8 beschreibt `spielt` mit gleicher Kennung (kein Warten, 9.4) und das Warten im Zustand `unbekannt` (Pause `leser_unbekannt`, Zeiger speichern, dann Warten); Sitzungstabelle um zwei Zeilen ergänzt; je ein Test.
7.  **Behoben.** `mqtt-v1.md` 4.2: Schritt 5 Konfiguration, Schritt 6 `ack`. `ha_ersatz.py` hielt die Reihenfolge schon ein (Test `test_gelernt_schreibt_gibt_konfig_geladen_und_bestaetigt_zugeordnet`); nur der Docstring wurde ergänzt.
8.  **Tests verbessert.** Der Test in `test_cuj07b_app.py` prüft jetzt `lern_wartet_bis` und den Zustand `spielt`. Der Neustart-Test ist auf CUJ-Ebene (`SimBox`, `lauf.json`, `DienstEndet`, Neustart, Hauptknopf). Neu: Leserausfall (Alarm, Hallo mit Herzschlag da und weg), Warten im Zustand `unbekannt`, „stumm“ (Beginn, Ende, Frist), `Gesperrt`, anderer Tobie (Sitzung und echter Kern), erneuter Lernbefehl im Warten, Fälle 1, 4 und 5.
