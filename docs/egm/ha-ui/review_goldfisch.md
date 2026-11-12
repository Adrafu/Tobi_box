# HA-Oberfläche: Review durch einen Goldfisch (EGM Schritt 3)

Gelesen: `design_draft.md`, `concepts_brief.md`, `brainstorm.md`, `ist.md`, `prototyp.html`, Vertrag W
(`docs/protocol/ha-websocket-v1.md`), `docs/data-model.md` (soweit verwiesen), dazu `__init__.py`, `http.py`, `websocket_api.py`,
`services.py`, `config_flow.py`, `media.py`, `hub.py`, `const.py` der Integration, `box/src/tobibox/sync.py` und die Tests unter
`homeassistant/tests/`. Der Prototyp wurde mit Chromium (Playwright) bei 390 und 1280 px, hell und dunkel, durchgeklickt.

**Zahl der Befunde: 26. Hoch 6, mittel 13, niedrig 7.**

## Kurzurteil

Der Entwurf trifft die Ziele: Die vier Kernaufgaben sind im Prototyp mit 1 bis 3 Taps erreichbar, die Begriffe sind sauber, die Tabelle
„alt → neu“ (Abschnitt 8) ist nahezu lückenlos. Der Prototyp hat keine Überläufe, keine Tap-Ziele unter 44 px und keine
Kontrastfehler (Skript über alle sieben Seiten in Hell und Dunkel: 0 Treffer). Die Schwächen liegen in drei Bereichen:
(1) **Rechte**: Die Aufteilung alltag/admin ist am WebSocket gut gedacht, wird aber von den HA-Aktionen umgangen, und „alltag“ erlaubt
mehr Schaden, als die Begründung in 9.2 sagt. (2) **Cover**: Die Ablage und die Suche sind nicht zu Ende gedacht. (3) **Bau**: Der Umbau
des Panels in einem Zug passt nicht zu „Tests nach jedem AP grün“.

## Befunde

### Hoch

**U1 · hoch · Abschnitt 9.3 (letzter Punkt), `services.py` Zeile 267 · HA-Aktionen sind gar nicht Admin-geschützt**
Problem: Der Entwurf schreibt, die HA-Aktionen „bleiben Administratoren vorbehalten (HA prüft das selbst nicht; das ist heute schon so)“.
Der zweite Halbsatz stimmt, der erste nicht: `services.py` registriert mit `hass.services.async_register(...)`. Damit darf jeder
angemeldete Benutzer die Aktionen über die HA-Schnittstelle (`call_service`) aufrufen, auch `tobibox.serie_loeschen`,
`papierkorb_leeren`, `liste_neu_ausrollen`, `sync_anstossen`, `update_anstossen`. Mit `require_admin=False` am Panel und mehr Benutzern
im Spiel ist die ganze Tabelle 9.2 wirkungslos: Wer Schaden anrichten will, nimmt den Umweg über die Aktion.
Vorschlag: Alle Aktionen, die in 9.2 „admin“ sind, mit `homeassistant.helpers.service.async_register_admin_service` registrieren
(prüft `is_admin`, wirft `Unauthorized`). Die Alltags-Aktionen (`zuordnen`, `loesen`, `lernmodus_*`, `leise_zeiten_setzen`,
`gute_nacht_setzen`) bleiben normal registriert. Neuer Test: Nicht-Admin ruft jede Aktion auf, erwartet `Unauthorized` bzw. Erfolg
nach Tabelle. Das gehört in U1 und ist ein eigener Befund, weil es auch heute schon gilt.

**U2 · hoch · Abschnitt 9.2 und Begründung, `hub.py` `zuordnung_setzen` · „Alltag“ kann die ganze Liste zerstören oder zumüllen**
Problem: Die Begründung „nichts endgültig zerstören“ trifft für zwei Befehle nicht zu.
(a) `zuordnung/remove` ist Alltag und die Liste ist lesbar: Eine Schleife über `zuordnung/list` löscht alle Zuordnungen, jede Änderung
erhöht die Revision und überschreibt danach auch den Export auf dem NAS. Es gibt keine Versionen der Liste; die Sicherung ist damit
mit weg. (b) `zuordnung/set` nimmt **jede** hexadezimale Kennung (`RE_UID`), auch unbekannte. Wer tausende Kennungen anlegt, treibt die
Liste an die Grenze `KONFIG_MAX_BYTES` (256 KiB), danach gehen für alle (auch Tobias) keine Änderungen mehr (`konfig_zu_gross`).
Das ist kein Angriff gegen Elternhände, aber ein Fehler im Browser oder in einem Skript genügt. (c) Der Ersatz `ueberschreiben=true` ist
für jeden offen.
Vorschlag: Für Nicht-Admins (im Befehl, wie bei `einstellungen/set`): `zuordnung/remove` nur mit `erwartet_ziel` (Seite sendet es
immer, schützt vor Doppelklick und vor dem zweiten Fenster); `zuordnung/set` nur für Kennungen, die HA kennt (in `neue_tobies` oder
schon zugeordnet), sonst `kennung_ungueltig` oder ein neuer Code; höchstens N Änderungen je Minute und Benutzer. Zusätzlich (auch
für Tobias nützlich): die letzten 10 Stände der Liste als `export/config.<n>.json` behalten und im Bereich „Für Tobias“ anzeigen.
Ist das zu viel, bleibt als Mindestes: `remove` für Nicht-Admins nur mit `erwartet_ziel`, und die Begründung in 9.2 ehrlicher
formulieren.

**U3 · hoch · Abschnitt 9.1, 13 Frage 1 · „Alle angemeldeten Benutzer“ ist ein weiterer Kreis als „Verena“**
Problem: In HA-Haushalten gibt es oft ein Wandtablet im Dauerbetrieb, ein Gästekonto, Konten für Familienmitglieder, die nur Licht
schalten sollen, und langlebige Zugriffstoken für Skripte. Alle bekommen mit dem Entwurf Zuordnen, Lernmodus, Hochladen (bis 500 MB
je Datei, ohne Obergrenze insgesamt, ohne Zuordnung zu einem Benutzer) und Leise-Zeiten. Ist HA aus dem Internet erreichbar, gilt das
auch von dort. Die Empfehlung „Ja, alle sind Eltern“ ist für diesen Haushalt vielleicht richtig, aber nicht abgesichert.
Vorschlag: Einen Schalter in den Optionen der Integration, **„Wer darf die Alltagsseite bedienen?“**: „Alle Benutzer“ oder
„nur diese Benutzer“ (Mehrfachauswahl aus `hass.auth.async_get_users()`, ohne `system_generated`, ohne deaktivierte). Das Backend
prüft das in einer Hilfsfunktion `darf_alltag(connection.user)`; `hello.rechte.alltag` meldet es. Die Seite sieht damit auch ehrlich
„nur lesen“. Kleinere Ergänzung: Upload-Summe je Stunde (zum Beispiel 4 GiB) als Obergrenze, mit `zu_viele_uploads`-ähnlichem Code.
Die Frage 1 bleibt trotzdem für Tobias offen (unten).

**U4 · hoch · Abschnitt 4.5, 6.1, 7 (Tabelle „Tobie umstellen: 3 Taps“) · Tobies sind in der Liste nicht zu unterscheiden**
Problem: Nach dem Zuordnen hat ein Tobie keinen Namen (der Name ist in der „Fertig“-Karte nur ein Knopf „Namen geben“). Im Prototyp
sind es sofort zwei Zeilen „Tobie ohne Namen · spielt „Lange Serie““ untereinander; bei 20 Figuren sind es viele. Die Aufgabe „Tobie auf
ein anderes Hörspiel umstellen“ oder „diesen Tobie vergessen“ lässt sich dann nicht lösen: Verena sieht keine Kennung (gewollt), kann
die Figur nicht „auflegen, um sie in der Liste zu finden“ (der Entwurf hat das nicht) und kann nicht raten. Die 3 Taps in Abschnitt 7 stimmen
nur, wenn man die richtige Zeile schon kennt.
Vorschlag: (1) Der Name wird beim Zuordnen **mit abgefragt**, als Textfeld direkt in der Fertig-Karte (nicht als Blatt hinter einem
Knopf), mit Beispiel „zum Beispiel Farbe oder Tier“, überspringbar, aber auffordernd. (2) Die Liste bekommt „Zuletzt zugeordnet“ oben
(braucht ein Zeitfeld je Zuordnung: neues optionales Feld in der HA-Seite des Speichers, die Box ignoriert es, oder wenigstens die
Reihenfolge der Einfügung beachten). (3) Auflegen-zum-Finden: Meldet die Box beim Auflegen die Kennung (`status`-Feld für den
Vertrag, falls schon vorhanden), hebt die Seite die Zeile hervor. Fehlt das Datenfeld, bleibt (1) und (2).

**U5 · hoch · Abschnitt 10 W-1 (Woher das Bild kommt), 9.2 `medien/pruefen` · Cover-Suche läuft ohne „schon versucht“-Marke bei jedem Öffnen**
Problem: `medien/pruefen` läuft laut Entwurf beim Öffnen der Seite (Abschnitt 8, Zeile „Freigabe prüfen“) und ist für alle Alltag. Es holt
„fehlende Cover“ nach. Serien ohne eingebettetes Bild haben **immer** ein fehlendes Cover; ohne Marke startet `ffmpeg`/`ffprobe` damit bei
jedem Seitenaufruf jedes Benutzers für jede dieser Serien neu, über SMB auf dem NAS, bei großen `.m4b`-Dateien (mehrere 100 MB, das
Cover liegt oft am Dateiende) langsam. „Höchstens eine Serie je Sekunde“ ist nur ein Tempo, kein Ende. Außerdem braucht die Extraktion
`ffmpeg` (nicht nur `ffprobe`); der Entwurf sagt nicht, was geschieht, wenn es fehlt (`ffprobe_fehlt` gibt es nur für ffprobe).
Vorschlag: Eine Marke je Serie, dass nach Cover gesucht wurde (Ergebnis `tags` oder `keine`, mit Zeit), zu speichern in `serie.json`
(unbekannte Felder bleiben erhalten, Abschnitt 1.4 des Datenmodells; die Box ignoriert sie) oder im HA-Speicher. Nachholen nur
(a) einmal nach dem Start der Integration im Hintergrund, (b) für Serien ohne Marke, (c) mit Zeitgrenze je Datei (zum Beispiel 20 s) und
mit Abbruch bei `medien_nicht_erreichbar`. Neue Folgen in einer Serie mit Marke `keine` lösen einmal eine neue Suche aus. Fehlt `ffmpeg`:
Fähigkeit `cover` nicht melden, Seite zeigt Platzhalter, keine Fehlermeldung. `medien/pruefen` nicht bei jedem Öffnen aufrufen, sondern
höchstens alle 10 Minuten und nur, wenn die Seite sichtbar ist.

**U6 · hoch · Abschnitt 12 (AP U4 bis U10), Schlussabsatz · „Tests nach jedem AP grün“ ist mit dem Umbau nicht einzuhalten**
Problem: `panel.test.mjs` (64 Tests) und `panel_quiet.test.mjs` (57 Tests) prüfen Reiter, Dialoge und Texte des heutigen Panels über
DOM-Selektoren. U4 ersetzt Reiter, Routen und Dialoge, U5 bis U9 die Seiten: Nach U4 sind weite Teile der 121 Tests rot, bis U10 die
Selektoren „anpasst“. Dazu verlangt `panel.test.mjs` einen deutschen Text für **jeden** Code der Vertragstabelle (Abschnitt 7): Der
Entwurf (5.1) deckt etwa 19 Codes nicht ab (siehe U19). Das Risiko, dass beim „Anpassen“ Tests gelockert werden, ist real.
Vorschlag: Alt-Panel nicht umbauen, sondern **einbetten**. Die bestehende Komponente bleibt (umbenannt, zum Beispiel
`tobibox-technik`, mit einem Schalter, der ihre eigene Kopfzeile und Reiterleiste ausblendet) und wird in „Für Tobias“ gezeigt. Die
neue Alltagsseite entsteht daneben als neue Dateien mit eigenen Tests. So laufen die alten Tests unverändert weiter, „nichts geht
verloren“ ist durch die Tests belegt, und der Umbau der alten Seite entfällt. Erst danach, wenn Tobias will, wird „Für Tobias“ in
aufklappbare Karten zerlegt (heute U10), das ist Schönheit, keine Voraussetzung.

### Mittel

**U7 · mittel · Abschnitt 12 U1 und Reihenfolge · `require_admin=False` kommt zu früh**
Problem: U1 setzt `require_admin=False` im Panel, die neue Seite entsteht erst in U4 bis U10. In der Zwischenzeit sieht jeder
Benutzer die **alte** Technikseite mit allen roten Knöpfen (das Backend lehnt die Admin-Befehle ab, aber Alltagsbefehle wie
`zuordnung/remove` gehen). Ein Zwischenstand auf Tobias' HA wäre ein Risiko.
Vorschlag: In U1 nur die Rechte im Backend und `hello.rechte` ändern, `require_admin` bleibt `True` bis zur Abnahme (U13). Erst dann
ein eigener kleiner Schritt „Seite für alle öffnen“, mit Test in `test_init.py` (heute prüft er `require_admin is True`). Dafür in
U1 die Tabelle 9.2 zuerst mit einem Testbenutzer prüfen.

**U8 · mittel · Abschnitt 10 W-1 (Speicherort `cover.jpg`) · Verträglichkeit mit Sync, Zusammenführen, Papierkorb, Einsortieren ungeklärt**
Problem: Die Prüfung „zu prüfen beim Bau“ ist als Nebensatz notiert, hat aber Folgen.
(a) **Sync:** `box/src/tobibox/sync.py` schließt nur Systemdateien und `_upload`, `_papierkorb`, `eingang` aus. `cover.jpg` (bis 150 KiB)
wird auf jede Box synchronisiert und verbraucht SD-Platz und Schreibvorgänge für etwas, das die Box nicht braucht. MPD kennt `cover.jpg`
als Albumbild und liest es vielleicht ein. (b) **Zusammenführen:** Die Quell-Serie samt ihrem `cover.jpg` geht in den Papierkorb; hat die
Ziel-Serie keines, ist es weg, und die Marke aus U5 ist falsch. (c) **Eingang:** Bilder im Eingang („ignoriert“) gehen heute in den
Papierkorb (Abschnitt 11.10). Ein mitgeliefertes `cover.jpg`/`folder.jpg` im Hörbuch-Ordner wäre die bessere Quelle als das
eingebettete Bild, bleibt aber ungenutzt. (d) „Ein vorhandenes `cover.jpg` wird nicht überschrieben“: ein falsches oder hässliches
erstes Bild bleibt für immer; ersetzen kann nur Tobias von Hand auf dem NAS. (e) Das Datenmodell kennt keinen reservierten Dateinamen;
`liste_auf_platte` ignoriert Nicht-Audio schon, die Box-`library` auch (nur Audioendungen), das ist geprüft, aber nicht festgeschrieben.
Vorschlag: `cover.jpg` im Datenmodell (Abschnitt 5, additiv) als reservierte Datei der Serie aufnehmen; im Sync mit
`--exclude 'cover*.jpg'` ausnehmen oder die Entscheidung bewusst anders treffen und begründen; beim Zusammenführen das Cover der Quelle
übernehmen, falls die Ziel-Serie keines hat; im Eingang `cover.jpg`/`folder.jpg` vor dem eingebetteten Bild nehmen; ein Admin-Knopf
„Cover neu suchen“ (löscht Datei und Marke) in „Für Tobias“, damit ein falsches Cover nicht für immer bleibt. Testfälle: Sync mit
Cover, Zusammenführen, Wiederherstellen aus dem Papierkorb, Serie umbenennen (Ordnername bleibt, ID bleibt).

**U9 · mittel · Abschnitt 6.1 und 7 · „Neuer Tobie: 1 Tap“ ist die halbe Wahrheit**
Problem: (a) Die Seite muss offen sein; ohne Push (Frage 9) muss Verena selbst nachsehen. Am Handy heißt das: HA-App öffnen, Seitenleiste,
„Tobi Box“ (nach `ist.md` zwei Taps). Die Zählung „1 Tap“ lässt das weg, die „heute“-Zahl in Abschnitt 7 zählte es genauso nicht mit, aber
das Ziel „höchstens drei“ gilt für den ganzen Weg. (b) **Welche Figur ist das?** Die Karte sagt nur Box und Zeit. Kinder legen oft zuerst
einen unbekannten Tobie auf; bei zwei Karten ist die Zuordnung ein Ratespiel, und der Tap ist sofort gültig. (c) Die Kacheln in der Karte
liegen im Scrollbereich; ein Wischer mit Fehltreffer ordnet falsch zu (Rückgängig hilft nur 8 Sekunden, dann ist der Weg über U4
nötig).
Vorschlag: Ehrlich zählen („1 Tap auf der Seite, plus Öffnen“). Eine einfache HA-Automation als Vorlage in `homeassistant/README.md`
(„Neuer Tobie“ → Mitteilung auf das Handy, Tippen öffnet `/tobibox`), ohne neue Funktion. Die Karte soll „Lege den Tobie noch einmal auf,
wenn du nicht sicher bist“ **über** den Kacheln zeigen und bei mehr als einer Karte nur die oberste bedienbar machen. Wer sich vertippt:
„Rückgängig“ bleibt, bis die Karte mit „OK“ geschlossen wird (nicht 8 Sekunden).

**U10 · mittel · Abschnitt 9.2 `eingang/sortieren` (auch `sofort`) · „Sofort“ übergeht den Schutz vor halb kopierten Dateien**
Problem: Die Ruhezeit (120 s und gleiche Größe über 30 s, Vertrag 11.1) schützt davor, eine Datei einzusortieren, die ein Kopierprogramm
auf dem NAS noch schreibt. `sofort=true` hebt das auf. Im Entwurf ist `sofort` für alle Alltag, und „Jetzt prüfen“ steht in „Gerade eben“. Drückt
Verena das, während Tobias einen großen Ordner kopiert, entstehen verstümmelte Folgen.
Vorschlag: `eingang/sortieren` für Nicht-Admins ohne `sofort` (im Befehl prüfen, wie `einstellungen/set`); „Jetzt prüfen“ ruft ohne `sofort` auf
und sagt, dass Dateien erst nach 2 Minuten Ruhe dran sind. `sofort` bleibt bei Tobias.

**U11 · mittel · Abschnitt 6.3, 8, 13 Frage 2 · Sackgassen, wenn der Upload falsch einsortiert wird**
Problem: Das Einsortieren nach Tags legt bei leicht anderer Schreibweise ein **zweites** Hörspiel an („Lange Serie“ und „Lange serie“). Verena
sieht „bitte kurz ansehen“, kann umbenennen und „Passt so“ drücken, aber nicht zusammenführen und nicht löschen (beides Admin). Dasselbe
gilt für eine falsch hochgeladene Datei. Die Seite endet dann in „Frag Tobias“, und „Passt so“ ist die einzige Taste, die Verena findet,
obwohl nichts passt. Dabei sind `folge/delete` und `serie/delete` nicht endgültig (Papierkorb, Tobias kann zurückholen); nur
`papierkorb/empty` ist es. Die Begründung 9.2 („nichts endgültig zerstören“) spricht also eher **für** das Löschen in den Papierkorb als
dagegen.
Vorschlag: In der gelben Karte statt „Passt so“ zwei klare Wege: „Das ist richtig“ und „Das stimmt nicht“. „Das stimmt nicht“ öffnet
ein Blatt: „Anderem Hörspiel zuordnen“ (`folge/verschieben`, mit Rückfrage), „In den Papierkorb“ (`folge/delete`, mit der Rückfrage aus 11).
Das hieße `folge/verschieben` und `folge/delete` für Alltag öffnen; falls nicht gewollt (Frage an Tobias), dann dort „Tobias
benachrichtigen“ (HA-Mitteilung) statt einer Sackgasse. „Passt so“ ist außerdem nicht selbsterklärend; „Das ist richtig“ ist klarer.

**U12 · mittel · Abschnitt 4.4, 6.3 · „Hörspiel hinzufügen“ am Handy: Stolperstellen**
Problem: (a) „Ordner vom Computer wählen“ (`webkitdirectory`) funktioniert am Handy nicht verlässlich (iOS Safari: gar nicht, Android
Chrome: nur über die Systemauswahl); der Prototyp zeigt den Knopf auch bei 390 px. Eine Laiin tippt ihn und bekommt nichts oder etwas
anderes. (b) **Die Hörbuch-Frage** („Gehören die Dateien zu einem Hörbuch?“) ist für Laien schwer; nach Vertrag 11.3 gruppiert das Einsortieren
Dateien mit gleichem Album-Tag ohnehin zu einer Folge, die Frage wirkt nur bei Dateien **ohne** Tags. Wer bei 30 Kapitel-Dateien ohne Tags
„Nein“ nimmt, bekommt 30 Folgen (`tags_fehlen`), ohne es selbst zu reparieren (nur Tobias kann zusammenführen/löschen). (c) Es fehlt die
**Zielwahl**: Vom Start aus kann Verena nicht sagen „in dieses Hörspiel“ (nur über die Hörspiel-Seite, die Abschnitt 6.3 so nebenbei
erwähnt). (d) Der Upload bricht ab, wenn das Handy den Bildschirm sperrt oder die App in den Hintergrund geht (Safari und Chrome frieren
Seiten ein); ein Hinweis „Bildschirm anlassen, bis alle Dateien fertig sind“ fehlt, die Wiederaufnahme auch (Abbruch ist behandelt, aber
nicht der häufige Fall). (e) Die genannte Obergrenze „500 MB“ gilt für HA; ein vorgeschalteter Reverse Proxy (nginx
`client_max_body_size`, Cloudflare 100 MB) kann niedriger sein. Die Seite zeigt dann einen unverständlichen Fehler.
Vorschlag: (a) „Ordner wählen“ nur bei `matchMedia('(pointer: fine)')` zeigen. (b) Frage nur stellen, wenn keine Tags gelesen werden
können (kein Album), mit Beispiel („Ein Hörbuch besteht aus Kapiteln: Ja. Mehrere Folgen: Nein.“); oder Vorgabe „Ja“, wenn alle Dateien
gleich benannt und nummeriert sind. (c) Ein Schritt nach „Dateien wählen“: „In welches Hörspiel?“ mit „Automatisch (nach den Dateien)“
als Vorgabe und den Kacheln darunter (kein zusätzlicher Tap für den Normalfall). (d) Hinweiszeile unter dem Fortschritt. (e) Fehler 413
von einem Proxy als `datei_zu_gross` zeigen und in „Für Tobias“ die tatsächliche Grenze nennen.

**U13 · mittel · Abschnitt 6.3 Punkt 4, 10 W-5 · „Gerade eben“ hat keinen Zustand für „erledigt“**
Problem: Die Liste soll Einträge zeigen, „bis man sie mit „Passt so“ oder einem Tap auf „Öffnen“ erledigt hat“. Der Vertrag kennt diesen
Zustand nur für `pruefen` (Serie/Folge-Flag). Für `pruefen=false` („fertig“) und für „geht nicht“ gibt es nichts, was ein „erledigt“
speichert; `eingang/list` mit `erledigt` liefert immer die letzten 100 Einträge. Entweder bleibt jeder Eintrag für immer (die Liste wächst bis
100), oder die Seite merkt es im Browser (`localStorage`: nur für dieses Gerät, Tobias' Wunsch „hängt nicht an der Sitzung“ gilt dann
nicht mehr). Außerdem ist `quelle` („vom Handy“/„vom NAS“) in W-5 „wenn es nicht billig geht, entfällt es“: damit ist die Anzeige 6.3 (Punkt 4
und 8) nicht festgelegt, und die Tests können nichts prüfen.
Vorschlag: Entscheiden und festschreiben: Der Entwurf zeigt Einträge der **letzten 24 Stunden** (`fertig_am`) und blendet ältere aus;
„Erledigte ausblenden“ merkt nur das Gerät (ehrlich benennen). Kein neuer Serverzustand. `quelle` fest in den Vertrag aufnehmen (die
Integration weiß es: `registriere_upload` im Eingang), nicht „bei Bedarf“.

**U14 · mittel · Abschnitt 3 und 11 · Theme und Kontrast sind im Prototyp nicht belegt, im Entwurf nur versprochen**
Problem: Der Prototyp benutzt eigene Variablen (`--bg`, `--primary`, …), nicht die HA-Variablen aus Abschnitt 3 (kein `--primary-color`,
`--card-background-color` im Code gefunden). Die Aussage „Kontrast geprüft“ gilt also nur für die Prototyp-Farben, nicht für die HA-Standard-
Themes oder Themes von Tobias. Rechnet man mit den Standardwerten (`--primary-color` #03a9f4, Text darauf weiß): 2,8 zu 1, fällt durch. Auch
`--success-color` (#4caf50) und `--warning-color` (#ff9800) taugen auf Weiß nicht als Textfarbe. Der Entwurf löst das mit „der Bau nimmt
`--primary-color`, wo es reicht, sonst eine Ableitung“, das ist als Anforderung zu unscharf. Nicht genannt sind außerdem
`--text-primary-color` (Text auf Primärfläche), `--secondary-background-color`, `--ha-card-border-radius`, `--ha-card-box-shadow` (der
Entwurf setzt 12 px fest) und `hass.themes.darkMode`.
Vorschlag: Regel: Flächen (Karten, Hintergrund, Trennlinien) **aus HA-Variablen**; Text- und Statusfarben (Hinweis, Warnung, Fehler,
Erfolg) als **eigene Token**, aus `--primary-text-color`/`--card-background-color` mit `color-mix()` abgeleitet; Primärknopf: Fläche
`--primary-color`, Text `--text-primary-color`, und **zur Laufzeit** den Kontrast prüfen (kleine Funktion), bei unter 4,5 zu 1 auf
Schwarz oder Weiß umschalten. Ein Playwright-Lauf (U11) mit drei Themes (HA-Standard hell/dunkel, ein Theme mit sehr hellem Primär)
statt nur „hell/dunkel“. HA-eigene Elemente (`ha-card`, `ha-icon`) sparsam nutzen, weil sie sich zwischen HA-Versionen ändern; nur
`ha-menu-button` und `ha-icon` sind übliche Panel-Bausteine.

**U15 · mittel · Abschnitt 2.1, 2.2 · Reiterleiste unten neben der HA-Navigation**
Problem: (a) Die Grenze ist „Handy-Hochformat bis 899 px“ (Media Query). HA schaltet das Panel bei 870 px auf `narrow` und zeigt die eigene
Seitenleiste dauerhaft an, wenn nicht `narrow`. Zwischen 870 und 899 px sitzt die HA-Seitenleiste links, und die Leiste unten (laut
Prototyp `position: fixed`) liegt über der Leiste oder reicht darunter. Außerdem hängt die nutzbare Breite von der Seitenleiste (eingeklappt
56 px, ausgeklappt 256 px) ab, nicht von der Fensterbreite. (b) Eine fest unten sitzende Leiste springt auf iOS Safari beim Ein- und
Ausblenden der Adressleiste und wird von der Bildschirmtastatur hochgeschoben (Namensfeld in der Fertig-Karte, Suchfeld). (c) Die
HA-Companion-App hat eigene Systemleisten (Android-Navigation, iOS-Home-Balken); der Prototyp nutzt `env(safe-area-inset-bottom)`
(gut), ob die App die Werte liefert, ist nicht belegt. (d) Fünf Reiter à 75 px bei 390 px (Prototyp, gemessen) gehen auf; bei 320 px
und 200 % Zoom bleiben je 64 px, „Hörspiele“ und „Für Tobias“ in 12 px werden knapp.
Vorschlag: Statt Media Query die Eigenschaft `narrow` des Panels benutzen (HA gibt sie vor); Leiste nicht `fixed`, sondern als unterer
Teil eines Flex-Rahmens, der den Panelbereich ausfüllt (`height: 100%`, Inhalt scrollt, Leiste bleibt), damit sie nie unter die HA-
Seitenleiste läuft. Bei offener Tastatur (`visualViewport`) die Leiste ausblenden. Früh in der Companion-App (iOS und Android) von Tobias
prüfen lassen (eigener Schritt in U13). Keine Fehler zu erwarten, aber nachweisen.

**U16 · mittel · Abschnitt 4.6, 6.4, 7 · Abends: Zählweise, Stepper und der Gute-Nacht-Tobie**
Problem: (a) Abschnitt 7 nennt für „Gute Nacht ändern“ 3 Taps. Der Stepper geht in 5-Minuten-Schritten; von 30 auf 60 Minuten sind es 6
Taps, auf 240 sind es 42. Die Tabelle sagt „heute 3 + Tippen“, „neu 3“, ohne Verbesserung. (b) „Dann wird sie leiser über 1 Minute“
(Ausblenden) ist ein technischer Wert, der kaum geändert wird; er macht die Karte länger. (c) Den **Gute-Nacht-Tobie** kann Verena nur über
Weg A (neuer, unbekannter Tobie, Kachel „Gute Nacht“) anlegen. Ein bereits zugeordneter Tobie lässt sich nicht auf Gute Nacht
umstellen (Blatt „Anderes Hörspiel“ zeigt nur Hörspiele), und Weg B (Lernmodus) gibt es für Aktionen nicht (Abschnitt 8 nennt „Einzelne
Folge“, nicht „Aktion“). Die Hilfe „Nimm einen Tobie, der noch nichts spielt“ gilt dann nicht, wenn alle Tobies schon belegt sind.
Vorschlag: Für Dauer Schnellwahl-Knöpfe („15, 30, 45, 60, 90 Minuten“) statt Stepper, mit „Anderer Wert“ als Auswahlfeld; „Ausblenden“ nach
„Für Tobias → Weitere Einstellungen“. Im Blatt „Anderes Hörspiel“ und im Lernmodus-Weg die Kachel „Gute Nacht“ anbieten (Ziel `aktion`,
Alltag), „Status“ bleibt bei Tobias.

**U17 · mittel · Abschnitt 9.1 Punkt 4, 10 W-4, Vertrag 3.11 · `einstellungen/set`: Zeitzone und letzte-Schreiber-gewinnt**
Problem: (a) Die Seite sendet die Zeitzone „unverändert mit“. Der Befehl ersetzt das **ganze** Objekt `leise_zeiten`; fehlt `zeitzone`, gilt
`Europe/Berlin` (Vertrag). Ändert Tobias die Zeitzone, während Verenas Seite offen ist, sendet sie den alten Wert, und der Befehl
antwortet für sie mit `unauthorized` („Dafür fehlt dir die Berechtigung“): irreführend, und ein Nicht-Admin kann nichts dafür.
(b) Es gibt keine Versionsprüfung (`stand`) bei Einstellungen: Zwei Eltern an zwei Geräten überschreiben sich still (letzter gewinnt).
Gleiches gilt für `gute_nacht`.
Vorschlag: Für Nicht-Admins ignoriert das Backend `zeitzone` im Objekt und nimmt den gespeicherten Wert (statt `unauthorized`); nur
`lesezeichen_tage` bleibt Admin (kommt aus Sicht der Seite nie im Alltag vor). Ein optionales Eingabefeld `erwartet_revision` (Revision der
Liste, schon vorhanden) für `einstellungen/set`: stimmt sie nicht, Fehler `stand_veraltet`; die Seite lädt neu und zeigt die Fehlermeldung
5.1 (steht schon in der Tabelle).

**U18 · mittel · Abschnitt 10 (W-4), 9.3, Vertrag 2.1, 9 · Versionsregel und Vertragstext**
Problem: Das Hinzufügen von Feldern und Fähigkeiten (W-1, W-3, W-4, W-5) ist nach Abschnitt 9 additiv und braucht kein `v`. Die Lockerung der
Rechte ändert aber das Verhalten bestehender Befehle (bisher `unauthorized`, jetzt Erfolg), den Wortlaut der Regel in 2.1 und den
Satz W-19. Der Entwurf nennt das richtig „Ausnahme“, aber zwei Dinge fehlen: (a) Der Vertrag hat eine Änderungsliste mit Datum (kein „1.2“-Zähler;
„Erweiterungen v1.1“ sind Bezeichnungen in Abschnitt 10). „Version 1.2“ im Entwurf passt nicht dazu. (b) Alte Seiten im Zwischenspeicher
(vor Neuladen) kennen `rechte` nicht und blenden nach `darf_schreiben` aus; das ist harmlos, solange sie Befehle nicht ändern, aber
es fehlt in 9.3 der Satz dazu. Außerdem ist die Fähigkeit `rechte_stufen` überflüssig: Seite und Backend liegen im selben Paket, und
die Seite entscheidet nach `hello.rechte`. Drei neue Fähigkeiten (`cover`, `box_anzeigenamen`, `rechte_stufen`) sind für das
Zwischenspeicher-Problem aus Abschnitt 9 sinnvoll, aber `box_anzeigenamen` und `rechte_stufen` könnten schlicht „Feld da“ heißen.
Vorschlag: Im Vertragskopf einen Eintrag „Änderung 12.11. (HA-Oberfläche): …“ in der Form der anderen; kein „1.2“. Abschnitt 2.1 vollständig
ersetzen (nicht ergänzen), W-19 streichen, Prüfungsabschnitt „Prüfung gegen die HA-API“ um `async_register_admin_service` ergänzen (U1).
`hello.rechte` mit `alltag` nur dann, wenn U3 (Benutzerliste) kommt, sonst entfällt das Feld. `darf_schreiben` bleibt.

**U19 · mittel · Abschnitt 9.1, Frage an HA-Mechanismen · `require_admin=False` und Prüfung je Befehl sind sauber umsetzbar (Bestätigung mit Hinweisen)**
Dies ist die gewünschte Antwort auf Prüfpunkt 3, kein Fehler. Umsetzbar so: `panel_custom.async_register_panel(..., require_admin=False)`
setzt `Panel.require_admin`; HA liefert die Seite nur Benutzern aus, die das Panel sehen dürfen (Filter in `websocket_get_panels`);
der Eintrag in der Seitenleiste ist je Benutzer ausblendbar. WebSocket: für `lesen` und `alltag` kein Dekorator (nur Anmeldung,
wie heute alles Lesen); für `admin` weiter `websocket_api.require_admin` (äußerer Dekorator in `befehl(...)`, Parameter
`admin=True` wird zu `recht="admin"`). Im Befehl selbst `connection.user.is_admin` und `raise Unauthorized`, das HA in `unauthorized`
übersetzt; das `TobiboxFehler("unauthorized")` aus `fehler.py` tut es auch. HTTP: bei `TobiboxUploadView` nur `@require_admin`
entfernen; `request["hass_user"]` bleibt gesetzt. Drei Dinge fehlen im Entwurf: (1) U1 (Aktionen). (2) Das JavaScript der Seite liegt unter
`/tobibox_static/` **ohne Anmeldung** (`async_register_static_paths`), schon heute; es enthält keine Geheimnisse, sollte es auch nie.
(3) Die Seitenleiste ist nur Komfort: Wer die Adresse `/tobibox` kennt, kommt hin; dafür sorgt allein das Backend.
Einstufung mittel, weil die Umsetzung sauber ist, aber die drei Punkte oben in den Entwurf gehören.

### Niedrig

**U20 · niedrig · Abschnitt 5.1 · Fehlertabelle deckt nicht alle Codes ab**
Es fehlen etwa 19 Codes aus Vertrag Abschnitt 7 (`anfrage_id_konflikt`, `box_unbekannt`, `datei_existiert`, `eintrag_nicht_gefunden`,
`export_nicht_gefunden`, `export_ungueltig`, `folge_nicht_gefunden`, `kein_lernmodus`, `kennung_ungueltig`, `konfig_zu_gross`,
`reihenfolge_ungueltig`, `rueckfrage_abgelaufen`, `serie_existiert`, `serie_nicht_gefunden`, `sortierung_laeuft`, `tobies_betroffen`,
`ueberraschung_existiert`, `upload_laeuft`, `ziel_ungueltig`; `invalid_format` steht nur als Wort). Der bestehende Test verlangt einen Text für jeden. Für
Alltag besonders wichtig: `rueckfrage_abgelaufen` (Lernmodus), `kein_lernmodus`, `serie_nicht_gefunden`, `folge_nicht_gefunden`,
`sortierung_laeuft` („Es wird gerade einsortiert. Versuche es in einer Minute noch einmal.“), `upload_laeuft`.
Vorschlag: Tabelle in `texte.js` vollständig ableiten; die Alltagscodes in 5.1 ergänzen, den Rest als „Standardtext“ mit Code nur für Admins.

**U21 · niedrig · Abschnitt 4.1.1, 10 W-3 · Box-Namen und Folgen-Namen**
(a) „Box Mond spielt …“: Trägt der Anzeigename schon „Box“ oder ist es „Lisas Box“, steht „Box Lisas Box spielt“. Der Satz soll den Namen
unverändert einsetzen („Mond spielt …“ oder „<Name> spielt …“), und die Optionen sollen sagen „Name ohne das Wort Box“. (b) `status.folge`
ist ein Dateiname (`folge-02.mp3`), der Anzeigename kommt aus `serie/get` (`folgen_info`): ein Aufruf je spielender Serie, nicht in `serien/list`.
Das steht nirgends. (c) Das Optionsformular (`config_flow.py`) kennt heute nur drei Felder; ein Feld je Box ist dynamisch. Einfach: ein Textfeld
„box1=Mond, box2=Stern“ mit der gleichen Prüfung wie `parse_boxen`, kein mehrstufiger Dialog.

**U22 · niedrig · Abschnitte 2.4, 4.7 · Begriffe**
(a) Der Reiter „Für Tobias“ trägt einen Personennamen: Ist ein zweiter Administrator, etwa Verena später, dabei, stimmt er nicht; Vorschlag
„Technik“ (Hinweiskarte darin: „Nur für Administratoren“). (b) Der Prototyp-Text „Verena sieht diese Seite nicht“ gehört nicht in das
Produkt; der Entwurf merkt das schon an. (c) „Passt so“, „Bitte kurz ansehen“, „Nicht merken“ sind nicht selbsterklärend (siehe U11); „Gerade
eben“ stimmt für Einträge von gestern nicht. (d) „Papierkorb“ taucht im Alltag nur in den Rückfragen auf; dort „Tobias kann es
zurückholen“ ist gut.

**U23 · niedrig · Abschnitt 1, 2, 4 · Einfachheit: was kann weg oder später**
Nichts ist falsch, aber für eine Laiin ist es viel: (a) Die **Wochenplan-Grafik** (sieben Balken, Legende, Textbeschreibung) und die
Zeilenliste darunter sagen dasselbe; die Grafik ist schön, aber 190 px Höhe und die kniffligste Stelle der Umsetzung (Mitternacht, U9). Für
Stufe 1 reichen die Zeilen („Mo–Do, So · 19:30 bis 06:30 · Stumm“); die Grafik später. (b) **„Reihenfolge ändern“** mit Modus, ▲/▼ und
eigenem Fokus ist für Folgen eines Hörspiels, die meist durch Tags richtig stehen, selten nötig; für Stufe 1 Tobias. (c) **Start**
zeigt Statuskarten, Neuer Tobie, zwei Knöpfe, Hinweiskarte und Kacheln; der Reiter „Hörspiele“ zeigt dasselbe Raster noch einmal. Wer
den Reiter „Hörspiele“ streicht und „Alle ansehen“ auf der Startseite lässt, spart einen Reiter (vier statt fünf für Admin, drei statt vier für
Verena). (d) Die zweite Zeile der Statuskarte („Neue Zuordnungen kommen auf die Box …“) erscheint auch bei Normalbetrieb kurz nach
jeder Änderung; ein dauernd wechselnder Satz macht unruhig. (e) „Name ändern“ je Folge: selten; im Blatt „Mehr“ statt als Knopf in jeder Zeile
(spart pro Zeile einen 44-px-Knopf).

**U24 · niedrig · Abschnitt 11 · Barrierefreiheit: Einzelheiten**
(a) **Fokusfalle im Shadow DOM:** `document.activeElement` liefert dort das Host-Element; die Prüfung muss `getRootNode().activeElement` benutzen.
Das gilt auch für die Rückkehr des Fokus nach Dialogen und für `aria-modal`-Hintergrund (`inert` auf dem Seitenrahmen ist einfacher als eine
eigene Falle, und das native `<dialog>` mit `showModal()` liefert Esc, Falle und Rückkehr kostenlos). (b) Die orange Marke „bitte ansehen“
verdeckt in der Karte „Neuer Tobie“ den Anfangsbuchstaben (Prototyp, 390 und 1280 px, Kachel „Test-Serie“). (c) Die Rückmeldung „Fertig“ ersetzt die
Karte (Höhe ändert sich) während des Scrollens: der Fokus soll auf der neuen Karte stehen (`aria-live` allein genügt nicht für Tastaturnutzer).
(d) Reiterbeschriftung 12 px ist die einzige Schrift auf der Grenze; bei Systemschrift „groß“ (Android) bricht „Hörspiele“. (e) Die rote Zahl am Reiter
„Start“ (nur Farbe und Zahl) braucht einen Text für Screenreader („1 neuer Tobie“).

**U25 · niedrig · Abschnitt 12 · Schnitt und Reihenfolge der Arbeitspakete**
(a) **U8** (Hinzufügen) ist das größte Paket: Dateien/Ordner/Ziehen, Warteschlange, Fortschritt, Eingang-Anbindung, Gründe, NAS-Einträge.
Teilen: U8a Hochladen mit Fortschritt (nur Handy-Weg), U8b Eingang-Anbindung („Gerade eben“, Gründe-Texte, NAS-Einträge). (b) **U1, U2, U3** (Rechte,
Namen, Cover) hängen nicht von der Seite ab und lassen sich parallel bauen; U3 braucht vorher U5 (Marke) und U8 (Sync). (c) Ein AP „Texte“
(`texte.js` mit Tabellen aus 5.1 und 6.3, vollständig gegen den Vertrag geprüft) vor U5 bis U9 erspart doppelte Arbeit. (d) U11
(Playwright) ist „optional ausgeführt“: der Entwurf lebt von den Aussagen aus 11; ohne Lauf sind sie unbelegt. Mindestens ein kleines Skript
(Tap-Ziele, kein waagerechter Scroll, Kontrast, 3 Themes) als Pflicht. (e) Neue Tests für die Alltagsrechte sind in U1 beschrieben und gut;
dazu `test_services.py` (U1 oben). (f) Reihenfolge: U1 und U2 zuerst (ohne die Seite zu öffnen, siehe U7), dann U0 (Vertrag) zusammen mit U1,
nicht davor (der Vertrag soll beschreiben, was gebaut ist).

**U26 · niedrig · Abschnitt 9.2 (Stufe „lesen“) · Lesebefehle für Alle**
`konfig/export_lesen` (liefert die ganze Liste inklusive aller Kennungen, im Alltag unnötig), `boxen/list` mit `ereignisse` (rohe
Meldungen und Fehlertexte der Box) und `eingang/list` mit allen Dateinamen sind für Alltagsbenutzer weiter lesbar. Nichts davon ist geheim, aber
der Entwurf sollte es bewusst so festlegen („Lesen bleibt für alle“) und `konfig/export_lesen` für Nicht-Admins weglassen, weil es nur
Tobias braucht (Liste im Detail).

## Prüfung der fünf Aufträge in Kürze

**1. Ziele erreicht?** Ja im Prototyp. Nachgeklickt (390 und 1280 px): (a) Start → Kachel: 1 Tap, grüne Fertig-Karte, „Rückgängig“ vorhanden.
(b) Kachel → „Auf Box Mond“ → Warteseite: 2 Taps; die Box ohne Strom ist grau mit Erklärung (gut). (c) „Hörspiel hinzufügen“ → „Dateien
wählen“: 2 Taps (+1 bei Hörbuch-Frage), Fortschritt in drei Schritten, drei Endzustände. (d) „Abends“ → Stepper → „Speichern“: 3 Taps für einen
Schritt; ein größerer Wert braucht mehr (U16). Stolperstellen für eine Laiin: U4 (Tobies nicht unterscheidbar), U9 (welche Figur?), U11 (Sackgassen),
U12 (Hörbuch-Frage, Ordner-Knopf am Handy), U16. Besonders gelungen: Satz-Status, Fehler mit nächster Handlung, Löschen abgesetzt, Rückgängig statt
Rückfrage.

**2. Nichts verloren?** Tabelle 8 deckt alles aus `ist.md` ab. Zu klären (kein Verlust, aber Lücke im Alltag): Gute-Nacht-Tobie für schon
belegte Figuren und per Lernmodus (U16); Entscheidungen der Warnleisten `leer_neu` / `export_neuer` liegen nur bei Tobias (gewollt). Die
Reiter „Boxen“ und „Korb“ sind vollständig in „Für Tobias“ (am sichersten durch Einbetten der alten Seite, U6).

**3. Rechte** siehe U1 bis U3, U10, U17, U19. Kurz: Der Schnitt alltag/admin ist bis auf `zuordnung/remove`, `zuordnung/set`, `eingang/sortieren sofort`
und `einstellungen/set` (Zeitzone) vernünftig; die HA-Aktionen laufen am Schutz vorbei (U1).

**4. Vertragsänderungen** siehe U5, U8, U13, U18, dazu **Signierte URLs** (unten). Cover-Ablage `cover.jpg` ist machbar, braucht die in U8
genannten Festlegungen.

**Signierte URLs in HA (Prüfpunkt 4, Teil 2):** `hass.auth.async_sign_path(hass, path, timedelta(hours=1))` ist der richtige Mechanismus für
`<img src>`; HA prüft die Signatur in der Anmeldung vor dem Handler (`requires_auth=True`), das Cover braucht dann kein eigenes Bearer-
Handling. Drei Fallen: (a) Die Signatur deckt Pfad **und** alle Abfrageparameter ab. Ein später angehängtes `?v=<cover_stand>` ungültig macht sie; das
Beispiel im Entwurf (`…?authSig=…`) ist richtig, aber `cover_stand` muss im signierten Pfad stehen. (b) `Cache-Control: max-age=86400` und `ETag`
helfen nicht, denn der Browser-Zwischenspeicher richtet sich nach der **vollen** URL, und `authSig` ändert sich mit jeder Signierung (bei jedem
`serien/list`, mindestens alle 45 Minuten): Alle Cover werden alle 45 Minuten neu geladen, und die Kacheln flackern beim Wechsel. (c) Ereignisse
(`medien`, `snapshot`), die an mehrere Abos gehen, dürfen kein `cover_url` tragen, weil die Signatur an die Sitzung des Benutzers gebunden ist
(`async_sign_path` nimmt das Aktualisierungstoken der aktuellen Verbindung); `cover_url` nur in Antworten auf Befehle.
Besserer Weg: Bild mit `hass.fetchWithAuth(url)` (Bearer, der Endpunkt kann ihn schon, laut W-1) laden, als `blob:`-URL halten und über
`cover_stand` als Schlüssel zwischenspeichern. Dann gibt es keine Signatur, keinen Ablauf und kein Flackern; die Signatur bleibt als
Rückfall. Als Aufwand klein, aber das Format von `cover_url` im Vertrag ändert sich (nur noch eine feste Adresse).

**5. Handy und Barrierefreiheit** siehe U14, U15, U24. Tap-Ziele, Kontrast und Überlauf im Prototyp bestanden; offen: Theme-Übertragung auf
echte HA-Farben (U14), Reiter und Seitenleiste (U15), Shadow-DOM-Fokus (U24).

## Fragen, die nur der Auftraggeber entscheiden kann

1. **Wer darf Alltag?** Alle HA-Benutzer (Entwurf) oder nur eine Liste von Benutzern (U3)? Gibt es ein Wandtablet oder Gäste mit Konto?
2. **Darf Verena Dinge in den Papierkorb legen** (`folge/delete`, `serie/delete`, `folge/verschieben`), damit sie nach einem Fehl-Upload nicht
   bei „Frag Tobias“ endet (U11)? Der Papierkorb bleibt, nur das Leeren ist endgültig und bleibt bei Tobias.
3. **Wie sicher soll die Liste sein?** Reicht eine einfache Sperre (U2: `remove` nur mit `erwartet_ziel`, nur bekannte Kennungen), oder soll es
   zusätzlich einen Verlauf der letzten Stände geben (bessere Sicherung, etwas mehr Arbeit im Backend)?
4. **Mitteilung auf das Handy** bei einem neuen Tobie (Frage 9, Empfehlung „nein“): Als HA-Automation (ohne neue Funktion) wäre es eine Vorlage in der
   Doku. Soll sie mitgeliefert werden?
5. **Namenspflicht beim Zuordnen** (U4): Soll die Seite nach dem Namen fragen (Textfeld in der Fertig-Karte, überspringbar) oder nur anbieten?
6. **Eigenes Foto und „Cover neu suchen“** (Frage 7, U8): Reicht in Stufe 1 ein Admin-Knopf „Cover neu suchen“ in „Für Tobias“, oder soll Verena
   ein Cover selbst ersetzen können?
7. **Stufe 1 schlanker?** Wochenplan-Grafik und „Reihenfolge ändern“ später (U23), ja oder nein?
8. **Gute-Nacht-Tobie auch für schon belegte Tobies und im Lernmodus** (U16): Ja (kleine Alltagserweiterung: Kachel „Gute Nacht“ im Blatt
   „Anderes Hörspiel“) oder bewusst nur über „Neuer Tobie“?
9. **Sync von `cover.jpg` auf die Boxen** (U8): ausnehmen (Empfehlung) oder mitnehmen (Cover für ein späteres Display)?
10. **Reiter „Für Tobias“ oder „Technik“** (U22) und Reiter „Hörspiele“ behalten oder streichen (U23)?
