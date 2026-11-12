# HA-Oberfläche: Bestandsaufnahme (Ist-Stand)

Stand: 12.11.2026. Grundlage für das neue UI-Konzept (EGM, Schritt 1).
Quellen: `homeassistant/custom_components/tobibox/frontend/tobibox-panel.js` (Zeilenangaben „L…“),
`homeassistant/README.md`, `docs/protocol/ha-websocket-v1.md`, `docs/protocol/mqtt-v1.md` Abschnitt 6,
`box/src/tobibox/ha.py`, `homeassistant/tests/frontend/mock-hass.mjs`.
Gelesen und beschrieben wurde nur, am Code wurde nichts geändert. Die Bilder entstanden mit dem Mock
(Testdaten: „Die drei ???“, „Bibi Blocksberg“, Boxen „Küche“ und „Kinderzimmer“), nicht mit echten Daten.

## 0. Kurzbild

* Eine einzige Seite „Tobi Box“ in der HA-Seitenleiste (Symbol `mdi:speaker-wireless`), **nur für Administratoren**
  (`require_admin=True`, README Schritt 3).
* Aufbau wie eine App: Kopfzeile, Inhalt, **untere Tab-Leiste mit 5 Reitern**, Einstellungen über ein Zahnrad.
* Alles besteht aus Karten und Knöpfen. Es gibt keine Tabellen. Maximalbreite 720 px, mittig (L1626).
* Was Eltern täglich bräuchten (Wer spielt gerade? Akku?) steht **nicht** in der Seite, sondern nur in HA selbst
  (Abschnitt 5).

## 1. Seitenaufbau

### 1.1 Rahmen (immer sichtbar)

| Teil | Inhalt (genau) |
|---|---|
| Kopfzeile (blau, klebt oben) | Titel **„Tobi Box“**; rechts ein Ladekreis (während Abfragen laufen), Zahnrad **⚙** (Beschriftung nur für Screenreader: „Einstellungen“), Pfeil **↻** („Neu laden“). Kein Menü-Knopf für die HA-Seitenleiste (im Code kein `ha-menu-button`; `narrow` wird nicht benutzt). |
| Meldungsleiste (unter der Kopfzeile, nur bei Bedarf) | rot: Fehler mit Knopf **OK**; blau/grau: Hinweis mit **OK**; orange: Warnungen zur Liste (siehe 1.8). Beim ersten Laden: „Lade …“. |
| Tab-Leiste (unten, fest) | **Serien** · **Eingang** (rote Zahl = offene Einträge) · **Tobies** (rote Zahl = neue, unbekannte Tobies) · **Boxen** · **Korb** (= Papierkorb). „Eingang“ und „Korb“ erscheinen nur, wenn das Backend die Fähigkeit meldet. |

### 1.2 Reiter „Serien“ (Startseite)

Zweck: Hörspiele/Hörbücher ansehen, hochladen, Serien anlegen.

1. Karte **„Hochladen“** (nur für Schreibberechtigte):
   Auswahl „In diese Serie einsortieren (Vorgabe)“ mit der ersten Option **„Nach den Tags entscheiden“** und
   allen Serien; Ankreuzfeld **„Die Dateien gehören zu einer Folge (ein Hörbuch)“**; Dateiwahl **„Dateien wählen“**
   (der Rest ist das Browser-Feld „Choose Files / No file chosen“, Sprache des Browsers);
   je Datei eine Zeile mit Name, Größe, Fortschrittsbalken und Status („wartet“, „37 %“, „wird geprüft …“,
   „angekommen“, „Warnung: … Die Datei bleibt im Eingang.“, Fehlertext); Knopf **„Liste leeren“**.
2. Je nach Zustand eine Karte/Leiste zur Überraschungs-Serie:
   „Es gibt noch keine Überraschungs-Serie. Die Box spielt sonst bei unbekannten Tobies einen Fehlerton.“ mit
   Knopf **„Überraschungs-Serie anlegen“**; „Es gibt mehr als eine Überraschungs-Serie.“;
   „Die Überraschungs-Serie ist noch leer.“
3. Knöpfe **„Neue Serie“** und **„Freigabe prüfen“**; darunter „Zuletzt geprüft: 09.11., 08:00“ oder „Prüfung läuft …“.
4. Liste der Serien, je Serie eine antippbare Karte: Name, Marke **„Überraschung“** (bei der Überraschungs-Serie),
   „3 Folgen · 2 Tobies“, orange Marke **„bitte prüfen (1)“**, orange Marke „n Hinweise“. Leer: „Noch keine Serien.“

Bild: `screens/01-serien-390.png`, `screens/01-serien-1280.png`.

### 1.3 Unterseite „Serie“ (Tippen auf eine Serie)

* Knopf **„‹ Serien“** (zurück).
* Karte mit Serienname (Überschrift), „3 Folgen · 2 Tobies“, orangen Hinweisen (technische Kurztexte, siehe 3),
  „Tobies auf die ganze Serie: Anna“, Knöpfe **„Umbenennen“**, **„Alles geprüft“** (nur bei „bitte prüfen“),
  **„Zusammenführen …“** (nicht bei der Überraschung), **„Serie löschen“** (rot).
* Karte „Dateien in diese Serie hochladen“ (Dateiwahl).
* Je Folge eine Karte: laufende Nummer, Anzeigename, Zeile „3 Tracks · 5.0 MB · Nr. 4 · Tobies: Anna, 04FF…BBAA“,
  Marken „bitte prüfen“ / „Warnung: …“, Knöpfe **„▲ Hoch“**, **„▼ Runter“**, **„Umbenennen“**, **„Verschieben“**,
  **„Geprüft“** (nur bei „bitte prüfen“), **„Löschen“** (rot). Die Karte lässt sich außerdem mit der Maus ziehen
  (Drag and drop, auf dem Handy ohne Wirkung; dort bleiben Hoch/Runter).
  Leer: „Noch keine Folgen.“

Bilder: `screens/02-serie-*.png`, `screens/03-serie-pruefen-*.png`.

### 1.4 Reiter „Eingang“

Zweck: Dateien, die hochgeladen oder aufs NAS gelegt wurden, werden nach ihren Tags einsortiert.

* Umschalter **„Im Eingang“** / **„Einsortiert“**.
* Knöpfe **„Erneut einsortieren“** und **„Sofort, ohne Wartezeit“**; darunter „Einsortieren läuft …“ oder „Zuletzt: 09.11., 08:30“.
* Überschrift **„Neu einsortiert“** (nur in dieser Sitzung): Karte je Eintrag mit Ergebnis-Zeilen „Der Rabe in „Die drei ???“
  (neue Serie)“, Marke „bitte prüfen“, Knöpfe **„Serie öffnen“**, **„Geprüft“**.
* Überschrift **„Liegt im Eingang“** bzw. **„Zuletzt einsortiert“**: Karte je Eintrag mit Name,
  „3 Dateien · 85.8 MB · blockiert“ (Status: wartet, bereit, läuft, blockiert, teilweise einsortiert, einsortiert),
  orangen Hinweisen (z. B. „Kopierschutz (a.m4b)“), Ergebnissen, Knopf **„Entfernen“** (rot, nur bei blockiert/teilweise).
  Leer: „Nichts im Eingang.“ Knopf **„Mehr laden“** ab 50 Einträgen.

Bild: `screens/04-eingang-*.png`.

### 1.5 Reiter „Tobies“

Zweck: Zuordnung Tobie → Serie/Folge/Aktion.

* Bei Sperre (Listenwarnung): Hinweis „Änderungen an den Zuordnungen sind gesperrt, bis die Warnung oben geklärt ist.“
* **„Neue Tobies“**: je unbekanntem Tobie eine Karte: gekürzte Kennung („0499…4433“),
  „2× gemeldet · zuletzt 09.11., 07:05 · kueche“, Knöpfe **„Zuordnen“**, **„Verwerfen“**.
  Leer: „Keine neuen Tobies. Lege einen unbekannten Tobie auf eine Box, dann erscheint er hier.“
* **„Lernmodus“** (Karte): „Die Box lernt den nächsten aufgelegten Tobie und ordnet ihn dem gewählten Ziel zu.“
  Knopf **„Neuen Tobie lernen“**; je Box ein Vorgang („kueche: Bitte jetzt den neuen Tobie auf die Box legen …“,
  Ziel, Knopf **„Abbrechen“** bzw. **„Schließen“**).
* Knopf **„Kennung von Hand eingeben“**.
* **„Zugeordnete Tobies“**: je Tobie Karte mit Name (sonst gekürzte Kennung), „04A1…E5F6 · Serie: Die drei ???“,
  Marken „Folge fehlt“/„Serie fehlt“, Knöpfe **„Name“**, **„Ziel ändern“**, **„Lösen“** (rot).
  Leer: „Noch keine Zuordnungen.“ Keine Suche, keine Sortierung, 100 pro Seite.

Bild: `screens/05-tobies-*.png`.

### 1.6 Reiter „Boxen“

Je Box eine Karte: Punkt grün/rot/grau + Name; „online · Liste aktuell“ (oder „offline“, „unbekannt“; Listenstand:
„Liste aktuell“, „Liste veraltet“, „Box hat neueren Stand“, „Stand unbekannt“); Zeile „Freier Speicher: 5120 MB · Netz: home ·
Akku: 80 % · Version 0.3.1“; „Sync: ok“; letzter Fehler (orange); aufklappbar „Letzte Meldungen (1)“; Knopf **„Sync jetzt“**
(grau, wenn die Box nicht online ist).
Darunter Karte **„Liste der Tobies“**: „Revision 7 · Export ok (09.11., 08:00)“, Knöpfe **„Liste neu ausrollen“** (rot) und
**„Export ansehen“**, danach z. B. „Export: Revision 9, 09.11., 10:00, 4 Zuordnungen (neuer als HA)“. Fußzeile „Integration 0.1.0“.

Nicht vorhanden: „spielt gerade“, Lader, Zustand der Wiedergabe.

Bild: `screens/06-boxen-*.png`.

### 1.7 Reiter „Korb“ und Einstellungen

**Korb:** Knopf **„Papierkorb leeren (n)“** (rot); je Eintrag Name, „Folge aus „Die drei ???“ · 1 Datei · 3.8 MB · 08.11., 11:00“,
Knöpfe **„Wiederherstellen“**, **„In andere Serie …“** (nur Folgen). Leer: „Der Papierkorb ist leer.“

**Einstellungen** (Zahnrad, eigene Unterseite mit **„‹ Zurück“**), drei Karten, je mit **„Speichern“** und **„Verwerfen“**:

* **„Leise-Zeiten“**: Erklärung „In diesen Zeiten spielt die Box leiser oder gar nicht. Ein Fenster gehört zu dem Tag, an dem es beginnt.“;
  Textfeld **„Zeitzone“** (z. B. Europe/Berlin); je **„Fenster n“**: Knopf „Löschen“, sieben Tag-Knöpfe Mo–So,
  Schnellwahl **„Alle“ / „Mo–Fr“ / „Sa, So“**, Uhrzeitfelder **„von“** und **„bis“**, Hinweis „Reicht über Mitternacht bis zum nächsten Tag.“,
  Umschalter **„Leiser“ / „Stumm“**, bei Leiser Regler „Höchste Lautstärke: 25 %“, bei Stumm „Die Box spielt nicht. Ein leiser Ton zeigt, dass der Tobie erkannt wurde.“;
  Knopf **„Fenster hinzufügen“**. Leer: „Keine Leise-Zeiten. Die Box spielt immer in der normalen Lautstärke.“
* **„Gute Nacht“**: „Mit der Gute-Nacht-Karte läuft ein Timer. Danach wird die Box leiser und hört auf.“;
  Felder „Timer in Minuten (1 bis 240)“ und „Ausblenden in Sekunden (5 bis 600)“.
* **„Lesezeichen“**: „Wurde ein Tobie so viele Tage nicht gespielt, beginnt er die Folge wieder von vorn. 0 heißt: nie.“; Feld „Tage (0 bis 365)“.

Bilder: `screens/07-papierkorb-*.png`, `screens/08-einstellungen-*.png`.

### 1.8 Warnleisten zur Liste (oben, über allem)

* Zustand `leer_neu`: **„Die Liste der Tobies ist leer.“** + „Der Speicher in HA ist leer, obwohl es schon einmal eine Liste gab. Bis du entscheidest, ändert sich nichts an den Boxen.“
  Knöpfe **„Aus dem Export holen“**, **„Mit leerer Liste neu beginnen“** (rot).
* Zustand `export_neuer`: **„Der Export auf dem NAS ist neuer als der Stand in HA.“** + „HA wurde wohl aus einer Sicherung zurückgespielt …“
  Knöpfe „Aus dem Export holen“, **„Stand von HA behalten“** (rot).
* „Die Sicherung auf dem NAS fehlt: Der Export konnte nicht geschrieben werden.“
* „Die Box kueche hat einen neueren Stand als HA. Bitte „Liste neu ausrollen“ (oder aus dem Export holen).“ mit zwei Knöpfen.

Solange so eine Warnung steht, sind „Zuordnen“, „Name“, „Ziel ändern“, „Lösen“, Lernmodus und alle Einstellungen gesperrt.
Bild: `screens/11-banner-liste-leer-*.png`.

### 1.9 Dialoge (am Handy von unten hochfahrend, am Desktop mittig)

| Dialog | Titel / Inhalt | Knöpfe |
|---|---|---|
| Text eingeben | „Neue Serie“ (Feld „Name“), „Serie umbenennen“ (Feld „Anzeigename“), „Folge umbenennen“, „Tobie-Name“ (Feld „Name (leer lassen für keinen Namen)“), „Kennung von Hand“ (Feld „Kennung des Tobies“) | Anlegen/Speichern/Weiter, Abbrechen |
| Serie wählen | „„Der Rabe“ verschieben nach …“, „Mit welcher Serie zusammenführen?“, „„…“ zurückholen in …“; Auswahl „Serie“ / „Bitte wählen“ | Weiter, Abbrechen |
| Ziel wählen | „Tobie zuordnen“ bzw. „Neuen Tobie lernen“: bei Lernmodus Auswahl „Box“; Umschalter **„Serie“ / „Einzelne Folge“ / „Aktion“**; Auswahl „Serie“, „Folge“ oder „Aktion“ (Status, Gute Nacht); Feld „Name des Tobies (freiwillig)“ | Weiter, Abbrechen |
| Rückfragen | „Zuordnung ändern?“, „Folge in den Papierkorb?“, „Serie „…“ in den Papierkorb?“, „Folge verschieben?“, „Serien zusammenführen?“, „Zuordnung lösen?“, „Papierkorb leeren?“, „Aus dem Eingang entfernen?“, „Liste neu ausrollen?“ / „Mit leerer Liste neu beginnen?“, „Aus dem Export holen?“; jeweils mit ausführlichem Satz und ggf. Liste betroffener Tobies | rot: „In den Papierkorb“, „Lösen“, „Zusammenführen“, „Endgültig löschen“, „Neu ausrollen“ …; Abbrechen |
| Lernmodus-Rückfrage (schiebt sich von selbst vor) | „Zuordnung überschreiben?“ „Dieser Tobie (04A1…E5F6) hat schon ein Ziel: …“ „Neu wäre: …“ „Antworte bis 10:03.“ | **„Überschreiben“** (rot), **„Behalten“** |

Bilder: `screens/09-dialog-zuordnen-*.png`, `screens/10-dialog-loeschen-*.png`.

## 2. Aufgaben und Aufwand

Gezählt: Taps/Klicks nach dem Öffnen der Seite (Seitenleiste „Tobi Box“ = zusätzlich 1 Klick; am Handy erst das HA-Menü,
dann Seite = 2) und ohne Tippen von Text. „Auswahl“ in einem Dropdown zählt 2 (öffnen, wählen). Die Zählung ist aus dem Code
abgeleitet, nicht mit einer Person gemessen.

| Aufgabe | Weg heute | Taps | Auffälligkeiten |
|---|---|---|---|
| **Tobie einer Serie zuordnen** (Tobie lag schon auf der Box) | Tobies → bei der Kennung „Zuordnen“ → Dialog: „Serie“ ist vorgewählt → Serie wählen (2) → ggf. Name → „Weiter“ | 5 (+Tippen des Namens) | Der Tobie wird nur an einer gekürzten Kennung erkannt („0499…4433“); bei mehreren neuen Tobies nicht zu unterscheiden. |
| … einer **einzelnen Folge** | wie oben, aber „Einzelne Folge“ → Serie wählen (2) → Folge wählen (2) → „Weiter“ | 8 | Die Folgenliste lädt nach der Serienwahl nach. |
| Bestehende Zuordnung ändern | Tobies → „Ziel ändern“ → Dialog → „Weiter“ → Rückfrage „Zuordnung ändern?“ → „Ersetzen“ | 6–9 | Zwei Bestätigungen. |
| **Unbekannten Tobie zuordnen** | Tobie auf Box legen (Box meldet) → Reiter „Tobies“ (rote Zahl) → wie „Serie zuordnen“. Alternativ **Lernmodus**: „Neuen Tobie lernen“ → Dialog (Box, Typ, Serie/Folge, Name) → „Weiter“ → Tobie auflegen → ggf. Rückfrage | 5–8 (+ Auflegen) | Nur die Kennung ist zu sehen; ohne Lernmodus keine Zuordnung zu einem bestimmten, gerade aufgelegten Tobie. Lernmodus ist auf derselben Seite versteckt unter den neuen Tobies. |
| **Hörbuch/Hörspiel hochladen und einsortieren** | Serien → Serie wählen (2, oder „Nach den Tags entscheiden“) → ggf. Häkchen „ein Hörbuch“ (1) → „Dateien wählen“ (1) + Dateiauswahl des Handys → warten. Danach in „Eingang“ nachsehen; Einsortieren läuft nach einer Wartezeit von selbst (oder „Sofort, ohne Wartezeit“). | 3–5 + Wartezeit | Der Ort des Ergebnisses ist nicht offensichtlich: Fertig heißt „angekommen“, einsortiert wird erst im Eingang; das Ergebnis erscheint in „Neu einsortiert“ (verschwindet beim Neuladen). Zwei Uploads gleichzeitig, mehr nicht. Verbindung weg: „Ob die Datei angekommen ist, zeigt der Eingang.“ |
| … mit **„bitte prüfen“** | Serien (orange Marke) → Serie → Folge prüfen (Name kontrollieren, ggf. „Umbenennen“ 3 Taps + Text) → „Geprüft“ oder „Alles geprüft“ | 3 (nur bestätigen) bis 7 (umbenennen) | Der Grund für „bitte prüfen“ wird nirgends erklärt (im Backend gibt es `pruefen_gruende`, die Seite zeigt sie nicht). |
| **Serie umbenennen** | Serien → Serie → „Umbenennen“ → Text → „Speichern“ | 3 + Tippen | |
| **Serien zusammenführen** | Serien → Serie → „Zusammenführen …“ → Zielserie wählen (2) → „Weiter“ → Rückfrage „Zusammenführen“ | 6 | Rückfrage nennt Folgen und Tobies, aber auch „Papierkorb“ für die Quelle. |
| **Serie löschen** | Serien → Serie → „Serie löschen“ → „In den Papierkorb“ | 3 | Nicht endgültig, aber der Begriff „Papierkorb“ (Reiter heißt „Korb“) wird nicht erklärt. |
| **Gute Nacht einstellen** | Zahnrad → Feld „Timer in Minuten“ → „Speichern“ (Entwurf; Zahl und Ausblenden getrennt) | 3 + Tippen (je Wert) | Das Feld stellt nur Dauer und Ausblenden ein. Die Auslösung ist ein Tobie mit Ziel „Aktion → Gute Nacht“: Tobies → „Zuordnen“ → „Aktion“ → Auswahl „Gute Nacht“ (Vorgabe ist „Status“) → „Weiter“ = 6. |
| **Leise-Zeiten einstellen** | Zahnrad → „Fenster hinzufügen“ (Vorgabe: alle Tage, 21:00–06:30, Stumm) → ggf. Tage/Zeiten/„Leiser“ + Regler → „Speichern“ | 3 (Vorgabe nehmen) bis ca. 12 | 12-Stunden-Anzeige „09:00 PM“, wenn der Browser englisch ist. Zeitzone ist ein Freitextfeld. Fehler zeigen „Stelle: Fenster 2, bis“. |
| **Lesezeichen-Tage** | Zahnrad → „Tage“ → „Speichern“ | 3 + Tippen | Begriff „Lesezeichen“ wird nur im Satz darunter erklärt. |
| **Lernmodus starten** | Tobies → „Neuen Tobie lernen“ → Dialog (Box 2, Typ, Serie 2, [Folge 2], Name) → „Weiter“ | 5–9 | Wird auch in HA an der Box angeboten (Knopf „Lernmodus abbrechen“, Auswahl „Serie für Lernmodus“, siehe 5); der Start selbst nur hier oder als HA-Aktion. |
| **Status der Boxen sehen** | Boxen | 1 | Sichtbar: online/offline, Listenstand, freier Speicher, Netz, Akku, Version, Sync, letzter Fehler. **Nicht** sichtbar: spielt gerade (Serie/Folge), Wiedergabe-Zustand, Lader. |
| **Sync auslösen** | Boxen → „Sync jetzt“ | 2 | Grau bei offline, ohne Erklärung. Antwort: „Sync angestoßen. Das Ergebnis erscheint im Status der Box.“ (zeigt dort „Sync: ok“ oder „idle“, roh). |
| **Papierkorb** (wiederherstellen, leeren) | Korb → „Wiederherstellen“ (2) oder „In andere Serie …“ (4); „Papierkorb leeren“ → „Endgültig löschen“ (2) | 2–4 | |
| **Export ansehen / Liste wiederherstellen** | Boxen → „Export ansehen“ (2). Sicherung selbst läuft automatisch nach jeder Änderung. Zurückholen: nur über die Warnleiste (1.8) „Aus dem Export holen“ → Rückfrage → „Aus Export holen“ (2); „Liste neu ausrollen“ → Rückfrage (2) | 2–3 | Die Warnleisten erklären mit NAS, Export, Sicherung, Revision und Listen-ID. Die Entscheidung dort ist für Laien nicht zu treffen (siehe 3). |

## 3. Fachbegriffe und technische Texte

Fundstelle = Zeile in `tobibox-panel.js`, sofern nichts anderes steht.

| Text | Wo | Problem für die Partnerin |
|---|---|---|
| **„Revision 7 · Export ok (09.11., 08:00)“**, „Export: Revision 9 … (neuer als HA)“, „Revision ${…}“ im Dialog | Boxen L1456, L1459; Rückfrage L821 | Revision = Versionszähler der Liste, nie erklärt. |
| **„Listen-ID“** („mit neuer Listen-ID an alle Boxen“) | L801, L821 | Interne Kennung. |
| **„Liste neu ausrollen“**, „HA verteilt den eigenen Stand … Boxen mit anderem Stand übernehmen ihn.“ | L798–L811, Knopf L1457 | Roter Knopf, dessen Wirkung nur Experten verstehen. |
| **Zustand `leer_neu` / `export_neuer`** (Meldungen „Die Liste der Tobies ist leer. Der Speicher in HA ist leer …“, „Der Export auf dem NAS ist neuer … HA wurde wohl aus einer Sicherung zurückgespielt“) | L1182–L1194 | Setzt Wissen über HA-Speicher, NAS, Backup voraus; die Wahl „Aus dem Export holen“ gegen „Mit leerer Liste neu beginnen“ (letzteres löscht alle Zuordnungen) ist gefährlich. Knopf „Stand von HA behalten“ ruft in Wahrheit „neu ausrollen“ auf (L1193). |
| **„Liste aktuell / veraltet / Box hat neueren Stand / Stand unbekannt“** | L189–L191, L1443 | Meint Abgleich Box ↔ HA, nicht „Sind die Hörspiele aktuell?“. |
| **„Die Sicherung auf dem NAS fehlt: Der Export konnte nicht geschrieben werden.“** | L1196 | NAS und Export unbekannt. |
| **Kennung / UID** („Kennung von Hand“, „Kennung des Tobies“, „04A1…E5F6“, „0499…4433“) | L752, L1389, L1400 | Hex-Kennung, mit 8+ Zeichen von Hand tippen; Fehler „Diese Kennung ist ungültig.“ (`FEHLERTEXTE`, Zeile 38). |
| **Serie, Folge, „Einzelne Folge“, Track, „Nr. 4“**, „Überraschung/Überraschungs-Serie“ | L1237ff, L1330 | „Überraschung“ ist Box-Fachwort: spielt bei unbekanntem Tobie. Track/„Nr.“ unklar. |
| **„Aktion: Status / Gute Nacht“** als Ziel eines Tobies | L193, L1136, L1607 | „Status“ (Box sagt Zustand an?) wird nirgends erklärt; Vorgabe der Auswahl ist „Status“. |
| **„Tags“** („Nach den Tags entscheiden“, „Hörbuch“-Häkchen) | L1261, L1264 | Gemeint: Titel/Album in den Dateien. |
| **„bitte prüfen“**, „Alles geprüft“, „Geprüft“, „n Hinweise“ | L1250, L1305, L1332 | Grund unbekannt; was „geprüft“ bewirkt, unklar. |
| **Hinweis-Texte** (`HINWEIS_TEXTE`): „Probedekodierung fehlgeschlagen“, „Prüfung nicht möglich“, „ffprobe fehlt“, „Doppelte Kennung korrigiert“, „Serien-Datei repariert“, „Reservierter Ordner“, „Kopierschutz“, „Verschieben fehlgeschlagen“, „Gewählte Serie fehlt“ | L168–L175 | Entwicklersprache; unbekannte Codes erscheinen roh (L176). |
| **Eingang** (Reiter, „Liegt im Eingang“, „Erneut einsortieren“, „Sofort, ohne Wartezeit“), Status „blockiert“, „teilweise einsortiert“ | L1347–L1370 | Zwischenstation, nirgends erklärt; „Wartezeit“ unbegründet. |
| **„Freigabe prüfen“** | L1243 | Freigabe = NAS-Freigabe; unverständlich. |
| **Fehlertexte** (`FEHLERTEXTE`): „Die Medien-Freigabe (NAS) ist gerade nicht erreichbar.“, „Der MQTT-Broker ist nicht erreichbar. Der Befehl wurde nicht gesendet.“, „Dafür sind Administratorrechte nötig.“, „Die Seite ist neuer als die Integration. Bitte die Seite neu laden (Strg+F5).“, „Dieser Vorgang wurde schon mit anderen Angaben gesendet.“, „Die Zuordnung wurde inzwischen woanders geändert. Die Ansicht wurde neu geladen.“, „Die Serie wurde inzwischen geändert …“, „Die Liste ist gesperrt, bis die Warnung oben geklärt ist.“, „Es zeigen Tobies darauf. Bitte bestätigen.“, „Dieses Dateiformat spielt die Box nicht.“ | L22–L61 | Viele sind Betreibersprache (NAS, MQTT-Broker, Strg+F5 ohne Tastatur am Handy). Nützlich sind sie nur halb: sie nennen die Ursache, nicht die nächste Handlung. Unbekannte Fehler: „Das hat nicht geklappt.“ |
| **Hinweise nach Speichern**: „Gespeichert. Die Boxen bekommen die Liste, sobald der Broker wieder erreichbar ist.“, „Das war schon so eingestellt.“, „Sync angestoßen. Das Ergebnis erscheint im Status der Box.“ | L729, L908–L910, L791 | „Broker“; die Box übernimmt nicht sofort. |
| **Box-Karte**: „Netz: home/hotspot/offline“ (roh, englisch), „Sync: ok“ / „idle“ / „laeuft“ + „(Grund)“, „Version 0.3.1“, „Freier Speicher: 5120 MB“, „Letzte Meldungen“ mit roher Art (z. B. `liste_abgelehnt`), letzter Fehler im Wortlaut der Box | L1443–L1452 | Technische Rohwerte statt Sätzen. |
| **Lernmodus-Zustände** („Die Box hat den Lernmodus abgelehnt.“, „Abgelaufen, es wurde kein Tobie gemeldet.“) und Rückfrage-Ablauf „Antworte bis 10:03.“ | L178–L186, L1431 | Zeitdruck (Minuten) und Box-Zustände. |
| **Zeitzone** („Europe/Berlin“), Fehler „Die Zeitzone ist unbekannt. Ein Beispiel: Europe/Berlin.“ | L1493, L118 | Freitext statt Auswahl. |
| **„Fenster“, „Wirkung“, „Höchste Lautstärke“, „Ausblenden in Sekunden“, „Lesezeichen“** | L1496–L1521 | Fachwörter der Leise-Zeiten; „Fenster“ = Zeitraum. |
| Tab **„Korb“** und „Papierkorb“ | L1216, L1465 | Wortbruch (zwei Namen für dasselbe). |
| „Integration 0.1.0“ | L1461 | Entwicklerinfo. |
| Kleinzeug am Gerät: Dateiauswahl „Choose Files / No file chosen“ und 12-Stunden-Uhrzeit folgen der Browsersprache, nicht der Seite | L1265, L1547 | Sprachmix. |

## 4. Mobil

Gemessen mit Chromium (Playwright 1.63, Chromium 1243), Breite 390 px (Handy) und 1280 px, Mock-`hass`
aus `mock-hass.mjs`. Bilder in `docs/egm/ha-ui/screens/` (PNG, ohne Skalierung):

| Bereich | 390 px | 1280 px |
|---|---|---|
| Serien | [01-serien-390](screens/01-serien-390.png) | [01-serien-1280](screens/01-serien-1280.png) |
| Serie (Folgen, Prüfen) | [02-serie-390](screens/02-serie-390.png), [03-serie-pruefen-390](screens/03-serie-pruefen-390.png) | [02-serie-1280](screens/02-serie-1280.png), [03-serie-pruefen-1280](screens/03-serie-pruefen-1280.png) |
| Eingang | [04-eingang-390](screens/04-eingang-390.png) | [04-eingang-1280](screens/04-eingang-1280.png) |
| Tobies | [05-tobies-390](screens/05-tobies-390.png) | [05-tobies-1280](screens/05-tobies-1280.png) |
| Boxen | [06-boxen-390](screens/06-boxen-390.png) | [06-boxen-1280](screens/06-boxen-1280.png) |
| Korb | [07-papierkorb-390](screens/07-papierkorb-390.png) | [07-papierkorb-1280](screens/07-papierkorb-1280.png) |
| Einstellungen | [08-einstellungen-390](screens/08-einstellungen-390.png) | [08-einstellungen-1280](screens/08-einstellungen-1280.png) |
| Dialog „Tobie zuordnen“ | [09-dialog-zuordnen-390](screens/09-dialog-zuordnen-390.png) | [09-dialog-zuordnen-1280](screens/09-dialog-zuordnen-1280.png) |
| Dialog „Serie löschen“ | [10-dialog-loeschen-390](screens/10-dialog-loeschen-390.png) | [10-dialog-loeschen-1280](screens/10-dialog-loeschen-1280.png) |
| Warnleiste „Liste leer“ (Tobies) | [11-banner-liste-leer-390](screens/11-banner-liste-leer-390.png) | [11-banner-liste-leer-1280](screens/11-banner-liste-leer-1280.png) |

Hinweis zu den Bildern: Die Seiten sind ganzseitig aufgenommen; die untere Tab-Leiste (fest am Bildschirmrand) erscheint dadurch
mitten im Bild. Das ist ein Aufnahmeeffekt, kein Fehler der Seite. Der Mock zeigt Browsertexte („Choose Files“, 12-Stunden-Uhr)
in Englisch, weil der Test-Browser englisch ist.

Beobachtungen:

* **Gut:** Die Seite ist für das Handy gebaut: einspaltige Karten, Knöpfe mindestens 48 px hoch (L1641), Dialog als Bottom-Sheet,
  kein Seitwärtsscrollen, keine Tabellen. Tab-Leiste fest unten mit 56 px Höhe, Inhalt hat 88 px Abstand dazu.
* **Kleine Ziele:** „Löschen“ je Fenster 44 px, Schnellwahl „Alle / Mo–Fr / Sa, So“ 44 px; Marken („bitte prüfen“, 12 px Schrift) und Meta-Zeilen (14 px, grau) klein;
  die sieben Wochentag-Knöpfe sind je etwa 43 px breit. Beschriftung der Tabs 14 px.
* **Lang:** Jede Folge ist eine Karte mit bis zu sechs Knöpfen (am Handy etwa 210 px hoch). Eine Serie mit 20 Folgen ergibt gut 4000 px Scrollhöhe; Löschen steht
  direkt neben Hoch/Runter/Umbenennen. Der Löschen-Knopf ist rot, aber ohne Abstand zum Nachbarn; mit Rückfrage abgesichert.
* **Reihenfolge ändern:** am Handy nur mit „▲ Hoch“/„▼ Runter“ Schritt für Schritt (Ziehen funktioniert nur mit Maus).
* **Menü fehlt:** Die Seite hat eine eigene Kopfzeile ohne HA-Menüknopf (Code-Befund, am Handy nicht probiert): Zurück zur HA-Seitenleiste nur über
  Browser-Zurück/Wischgeste.
* **Tab-Leiste:** fünf Reiter à etwa 78 px; die Zahlenmarken („Eingang 1“, „Tobies 1“) rutschen eng an den Text.
* **Breit (1280 px):** Inhalt bleibt auf 720 px, mittig; links und rechts leer; Knöpfe füllen die Breite der Karte (sehr breite Knöpfe).
* **Boxen-Karte:** Meta-Zeile mit Speicher, Netz, Akku und Version in einer Fließzeile (umbrechend), Akku nicht als eigene Zahl hervorgehoben.
* **Dateiauswahl:** native Browser-Eingabe, Beschriftung nicht anpassbar; am Handy öffnet sie die Dateiauswahl des Systems. Dateien aus Apple Books/Audible
  sind nicht erreichbar (kopiergeschützt, „Kopierschutz“).
* **Admin-Zwang:** Die Seite erscheint nur für Administratoren (README, Schritt 3). Die Partnerin bräuchte ein Admin-Konto in HA.

## 5. Was Home Assistant selbst schon bietet

Die Box legt per MQTT-Discovery **ein Gerät je Box** an („Tobi Box <Name>“, Hersteller „Tobi Box“, Modell „NFC-Audiobox“, `mqtt-v1.md` 6.1, `ha.py`).
Zu finden unter Einstellungen → Geräte & Dienste → MQTT → Geräte (oder über die Entitäten-Suche). Für Eltern nützlich:

| Entität | Typ | Bedeutung für Eltern |
|---|---|---|
| **Zustand** | Sensor | `leer`, `spielt`, `pausiert`, `beendet`, `gehalten`, `unbekannt`, `herunterfahren` (roh; Werte nicht übersetzt) |
| **Läuft gerade** | Sensor | Name der Serie oder „keine“ (die Folge nennt die Entität nicht) |
| **Akku** | Sensor (Batterie, %) | direkt brauchbar, HA zeigt Batteriesymbol |
| **Lader** | Binärsensor (lädt) | „Strom am Eingang“, unbekannt bei `null` |
| **Netz** | Sensor | home, hotspot, offline |
| **Sync-Stand** | Sensor + Attribute | `idle`, `laeuft`, `fehler`; Zeitpunkt, Ergebnis, Grund als Attribute |
| **Freier Speicher** | Sensor | nach Vorschlag in GB |
| **Letzter Fehler** | Sensor | Text der Box oder „kein Fehler“ |
| Version, Zeitquelle | Sensor (Diagnose) | nur für Technik |
| **Sync jetzt**, **Update**, **Lernmodus abbrechen** | Knöpfe | Sync ohne Panel; „Update“ spielt eine neue Box-Software ein (Gefahr bei Fehlbedienung) |
| **Serie für Lernmodus** | Auswahl | Vorbelegung (kein Befehl) für die HA-Aktion „Lernmodus starten“ |

Dazu kommt:

* **Dashboard:** Die Entitäten lassen sich in ein eigenes Dashboard legen (Karte „Entitäten“, „Batterie“ …). Wer das mit Tobias zusammenstellt, hat
  „Akku, spielt gerade, online, Sync jetzt“ auf einer Karte. Es wird von der Integration nicht mitgeliefert.
* **HA-Aktionen** (`services.yaml`: `zuordnen`, `loesen`, `lernmodus_starten`, `lernmodus_abbrechen`, `serie_anlegen`, `serie_umbenennen`, `serie_loeschen`,
  `folge_*`, `serien_zusammenfuehren`, `eingang_einsortieren`, `papierkorb_leeren`, `sync_anstossen`, `update_anstossen`, `liste_neu_ausrollen`,
  `leise_zeiten_setzen`, `gute_nacht_setzen`, `lesezeichen_tage_setzen`): für Automationen und Szenen (z. B. „abends Leise-Zeit“, „Knopf: Gute Nacht“),
  aber mit technischen Feldern (`serie_id`, `folge`); für Eltern nur über Tobias oder fertige Knöpfe.
* **Benachrichtigung:** Die Rückfrage des Lernmodus („Tobie hat schon ein Ziel“) geht zusätzlich als HA-Benachrichtigung (`persistent_notification`) hinaus
  (`lernmodus.py`); der Inhalt wurde hier nicht geprüft.
* **Medien-Browser:** Die Integration registriert keine Medienquelle (im Code keine `media_source`-Anbindung). Hörspiele erscheinen dort **nicht**;
  der Medien-Browser von HA hilft Eltern hier nicht. Die NAS-Freigabe wird (laut README) getrennt in HA eingebunden (`/media/tobibox`).
* **Nicht in HA:** Tobie-Zuordnungen, Serien/Folgen und Einstellungen (Leise-Zeiten, Gute Nacht, Lesezeichen) gibt es nur in der Panelseite oder als HA-Aktion.

## 6. Befunde für das Konzept (nur Material, keine Entscheidung)

* Zwei Welten: Panel (Zuordnen, Medien, Einstellungen, Sync) und HA-Gerätseite (Akku, spielt gerade, Zustand). Eltern müssen zwischen beiden wechseln.
* Die Hauptaufgabe „Tobie zuordnen“ steht auf dem dritten Reiter, mit einem Weg über Kennungen. Der Auslöser ist physisch (Tobie auflegen) und die
  Seite nennt den Tobie nicht beim Namen.
* Die gefährlichen Knöpfe („Liste neu ausrollen“, „Mit leerer Liste neu beginnen“) stehen am selben Ort wie harmlose Anzeigen (Boxen).
