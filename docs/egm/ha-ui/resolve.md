# HA-Oberfläche: Resolve (12.11.)

Grundlage: `review_goldfisch.md` (U1–U26), `design_draft.md` Rev. 2, Abschnitt 16 (offene Fragen), `brainstorm.md`
Runden 6 und 7. **(Tobias)** = von Tobias entschieden, **(Empf.)** = Empfehlung des Entwurfs, Tobias hat nicht widersprochen.

## Entscheidungen zu den offenen Fragen (Entwurf Rev. 2, Abschnitt 16)

| Nr. | Frage | Entscheidung |
|---|---|---|
| 1 | „Technik“ statt „Für Tobias“ | **(Tobias)** Knopf „Technik“ oben, nur für Admins sichtbar. |
| 2 | Die Partnerin stellt aus dem Papierkorb wieder her | **(Tobias)** Erst mal nein: Wiederherstellen und Leeren bleiben Admin. Nach einigen Wochen neu abwägen. |
| 3 | Letzte 10 Stände der Liste aufbewahren | **(Tobias)** Ja; Zurückdrehen nur Admin unter „Technik“. |
| 4 | Regeln für den Art-Vorschlag | **(Empf.)** An je fünf echten Dateien pro Art prüfen, bevor das Paket fertig ist; Korrektur über „Art ändern“. |
| 5 | `cover*.jpg` nicht auf die Boxen | **(Empf.)** Ja. |
| 6 | Wochenplan-Grafik später, „Reihenfolge ändern“ nur Admin | **(Empf.)** Ja. |
| 7 | Rückfrage beim Papierkorb nennt betroffene Tobies | **(Empf.)** Reicht. |
| 8 | Hördaten (Stufe B) sichtbar für | **(Tobias)** Alle HA-Benutzer; Löschen nur Admin. |
| 9 | Stufe B zählt je Box, nicht je Tobie | **(Empf.)** Ja; Kennung des Tobies später additiv, falls nötig. **(Tobias, Ergänzung)** Pflicht in „Gehört“: welche Box welches Hörspiel wie oft gehört hat (Anzahl, Hörzeit, fertig gehörte Folgen; je Box und gesamt; aufklappbar nach Folgen; Zeitraum wählbar). |
| 10 | Speicherplatz der Boxen | **(Tobias)** SD-Karten 128 GB; nach dem System gut 110 GB frei. 200 Hörbücher (etwa 50–80 GB) und 300 Lieder passen. Keine Auswahl je Box nötig; `speicher_frei` im Blick behalten. |
| 11 | Vorlage „Neuer Tobie → Mitteilung aufs Handy“ | **(Empf.)** Ja, in der Doku. |
| 12 | Stufe B vor C | **(Empf.)** Ja. |
| 13 | Seite erst nach Abnahme für alle öffnen | **(Empf.)** Ja. |

## Runde 7: Bibliothek und Reinhören

Siehe `brainstorm.md`, Runde 7: Bibliothek wie eine Hörbuch-App (Vorbild Audible), Reinhören nur am Handy/PC,
Weiterhören je Folge und je HA-Benutzer in HA gespeichert. Wird in Entwurf Rev. 3 und Prototyp v3 eingearbeitet.

## Nächste Schritte

1. Entwurf Rev. 3 und Prototyp v3 (läuft), Tobias sieht sich den Prototyp an.
2. Goldfisch-Review von Rev. 3 (frischer Agent, nur Dokument und referenzierte Dateien).
3. Befunde mit Tobias, dann Bau von Stufe A in Paketen.

## Runde 8 und 9 (Entwurf Rev. 3/4, Fragen 14–26)

| Nr. | Entscheidung |
|---|---|
| 14 | **(Tobias)** Abspiel-Link gilt 1 Stunde, still erneuert. |
| 15 | **(Tobias)** Reinhören dürfen alle HA-Benutzer. |
| 16 | **(Tobias)** Die Hörstelle (Weiterhören) sieht jeder nur für sich. |
| 17 | **(Tobias)** Alle Formate im Bestand → Hörkopien für Formate, die nicht jeder Browser spielt. |
| 18 | **(Tobias)** Dauer des Bestands einmal im Hintergrund nachlesen. |
| 19 | **(Tobias)** Ab 10 s zählt eine Wiedergabe; Unterbrechungen bis 5 min zählen als eine. |
| 20 | **(Tobias)** Hörbuch: Zeitleiste über alles **und** Kapitelliste (schon in Stufe A). |
| 21 | **(Tobias)** Reinhören wird erfasst, dem HA-Benutzer zugeordnet (Stufe B). |
| 22 | **(Tobias)** Musik spielt über das Album weiter, später über eine Playlist (Stufe C). |
| 23 | **(Tobias)** **Reinhör-Daten sehen alle HA-Benutzer** (nicht nur die eigenen). Die Hörstelle bleibt privat (Nr. 16). PL: Umschalter heißt „Boxen \| Reinhören“, darin Auswahl „Alle“ oder ein HA-Benutzer (Namen aus HA, nie im Repo); löschen darf jeder seine eigenen, Administratoren alles. Erfassung beginnt mit Stufe B. |
| 24 | **(Tobias)** Jedes einzelne Lied ist ein eigener Eintrag (Serie mit einer Folge, `einzeln: true`); der Tobie zeigt auf die Folge. |
| 25 | **(Tobias)** NAS-Eingang weiter automatisch, „Anders einsortieren …“ bei „bitte ansehen“; ist der Rückweg zu teuer, Rückfall nach Entwurf 16 Nr. 25. |
| 26 | **(Tobias)** NAS hat einige TB frei: Hörkopien auf dem NAS neben `medien/`, AAC 96 kbit/s, auch für FLAC und WAV. |

## Runde 10

| Nr. | Entscheidung |
|---|---|
| 23a | **(Tobias)** „Gehört“ ohne Umschalter Boxen/Reinhören und ohne Hinweistext: eine Auswahl „Wer?“ mit Alle, Box 1, Box 2 (Anzeigenamen aus HA) und den HA-Benutzern, die reingehört haben. |
| 25 | **(Tobias)** Rückfall wie im Entwurf: passt. |
| N | **(Tobias)** Echte Namen (Kinder und Eltern) nie im Repo; Prototyp im Repo mit Platzhaltern. |

## Goldfisch-Review Rev. 4a (`review_goldfisch_rev4.md`, G1–G31)

| Frage | Entscheidung |
|---|---|
| 1 Stufe A schneiden (G14) | **(Tobias)** Drei Teile mit je eigener Abnahme: **A-1** Alltag (Bibliothek, Tobies, Hochladen, Abends, Rechte), **A-2** Reinhören mit Weiterhören, **A-3** Hörkopien und Kapitel. |
| 2 Hörkopien wann (G1) | **(Tobias)** Neu Einsortiertes sofort, Bestand erst beim ersten Reinhören („Hörprobe wird vorbereitet“). Ersetzt für die Hörkopien den Hintergrund-Lauf über den Bestand (Nr. 18 gilt weiter für die Dauer). Grenzen aus G1 (Dauerdeckel, feste Zeitgrenze, Schlangenlimit) gelten. |
| 3 Upload-Grenze (G15) | **(Tobias)** Auf **2 GiB** je Datei anheben. |
| 4 Papierkorb für alle (G8) | **(Empf.)** Mitteilung an Administratoren plus „Letzte Stunde zurückholen“; kein Tageslimit. |
| 5 „Anders einsortieren“ (G9) | **(Empf.)** Nur für Einträge „bitte ansehen“ oder jünger als 24 Stunden. |
| 6 Gesperrtes Handy (G18) | **(Tobias)** Abspiel-Link gilt **24 Stunden** wie bei HA (ersetzt Nr. 14: 1 Stunde). |

Alle übrigen Befunde G1–G31 und die offenen U-Punkte (U2, U6, U8, U10, U15, U18, U22, U25) arbeitet Rev. 5 nach den Vorschlägen des Reviews ein.

## Runde 11 (Fragen 27–29 aus Rev. 5)

| Nr. | Entscheidung |
|---|---|
| Name | **(Tobias)** Die Karte heißt „Neuer Tobie auf <Name>s Box“: Der Anzeigename einer Box ist der ganze Name („Box 1“ bzw. in HA z. B. „Annas Box“). |
| 27 | **(Tobias)** Reinhör-Daten löschen nur in „Technik“ (Administrator); kommt praktisch nicht vor. |
| 28 | **(Tobias)** „Alle“ ist die Summe aus Boxen und Reinhören. |
| 29 | Erklärt; Grenzen nach Messung in A0b. |

## Freigabe A0 (12.11.)

- **(Tobias)** Vertragsänderungen A0 freigegeben (`a0_freigabe.md`, Entwurf in `a0_entwurf/`), inklusive der vier Ergänzungen des Agents
  (frühere Stände, `geloescht_von`, `pruefen` am Eingangs-Eintrag, `unauthorized` ohne `erwartet_ziel`). Übernommen nach
  `docs/protocol/ha-websocket-v1.md` und `docs/data-model.md`.
- **(Tobias)** Bestehende Tests dürfen im jeweiligen Paket angepasst werden, soweit `a0_freigabe.md` Abschnitt 4 sie nennt;
  jede Änderung einzeln im Diff und im Bericht.

## Runde 12 (12.11., UX-Durchsicht des Prototyps v5, von Tobias eingebracht)

**(Tobias)** Alle Punkte umsetzen, im Design und im Prototyp, vor dem Bau der Seite (A6 ff.):

| Nr. | Punkt | Umsetzung (PL) |
|---|---|---|
| X1 | Reiterleiste mit fünf Punkten zu voll | Höchstens **vier Reiter: Start, Bibliothek, Tobies, Mehr**. „Abends“ und „Gehört“ wandern nach „Mehr“. „Mehr“ sehen **alle** Benutzer (Abends ist Alltag für die Partnerin); „Technik“ bleibt der Admin-Knopf oben. |
| X2 | Reiter-Beschriftung 12 px | Beschriftung größer (mind. 13–14 px), bei vier Reitern immer sichtbar. |
| X3 | Leere Zustände wirken technisch | Freundliche, eigene Illustrationen (Inline-SVG, Farben aus Tokens) mit einem kurzen Satz und einem Knopf; keine fremden Marken oder Figuren. |
| X4 | Formsprache | Karten mit `border-radius` 16 px, Blätter und große Kacheln 24 px. |
| X5 | Hochladen zu textlastig | Wahl „Was lädst du hoch?“ mit großen Symbolen und kurzen Titeln, höchstens eine kurze Zeile Erklärung. |
| X6 | Mini-Player | Zusätzlich Wischen nach oben öffnet, nach unten schließt (Knopf bleibt für Barrierefreiheit). |
| X7 | Meldungen | Erfolg verschwindet nach etwa 4,5 s; **Fehler bleiben**, bis man sie wegwischt oder bestätigt. |
| X8 | Tippflächen in Listen | „Mehr“ (drei Punkte), Pfeile usw. mindestens 44 × 44 px, auch einhändig. |
| X9 | Kontrast im Theme mit hellem Primärton | Warn- und Hinweiskarten, Ränder und dünne Symbole mit mind. 3:1 Nicht-Text-Kontrast prüfen und sichern. |
| X10 | „Ändern“-Knöpfe in Listen (Tobies-Liste): springen je nach Textlänge hin und her, wiederholen sich, wirken schwer | **(Tobias, „echt ungut“)** PL: Ganze Zeile ist die Tippfläche (öffnet das Bearbeiten-Blatt), rechts ein ruhiger Pfeil „›“ an fester Stelle; keine wiederholten umrandeten Knöpfe in Listen. Gilt für alle Listen mit gleicher Aktion je Zeile. |
| X11 | Erklärtexte auf „Hinzufügen“ (erlaubte Formate, 2 GB, Kopierschutz, „Bildschirm anlassen“, NAS-Eingang-Hinweis) | **(Tobias)** Alles weg. Der Benutzer soll einfach machen; erst wenn etwas nicht geht, zeigt die Seite **genau diesen Fehler** mit dem, was zu tun ist (z. B. Format, Größe, Kopierschutz, Upload abgebrochen). Gilt sinngemäß für alle Seiten: keine vorsorglichen Erklärkästen. |
| X12 | Wo leben Playlists (Stufe C)? | **(Tobias)** In der **Bibliothek**, nicht unter „Mehr“, und sie funktionieren **wie bei Spotify**: Playlist anlegen, über „⋯“ bei jeder Folge/jedem Lied „Zur Playlist hinzufügen“, eigene Playlist-Seite mit Cover-Mosaik, Abspielen/Reinhören, Reihenfolge ziehen, Einträge entfernen, umbenennen; als Tobie-Ziel wählbar. Bau weiter erst in Stufe C. |

## Sammlung: Klarstellungen am Vertrag W (**K1–K5 von Tobias freigegeben, 12.11.**)

Beim Bau aufgefallen; der Code folgt jeweils der hier genannten Lösung (PL), der Vertragstext wird nach Freigabe gebündelt angepasst.

| Nr. | Stelle | Klarstellung |
|---|---|---|
| K1 | 14.2 `serien/list` ohne `limit` | „bisheriges Verhalten (alle)“, der Zusatz „höchstens 200“ entfällt (alte Seite braucht alle) |
| K2 | 14.3 Cover, 14.10 | Eine Funktion mit zwei Modi: Foto-Upload streng (JPEG, quadratisch, ≤ 2048 px), Tag-Bilder und mitgelieferte Dateien nachsichtig (verkleinern, mittig quadratisch zuschneiden); neue Konstante `COVER_NACHSICHT_PIXEL_MAX` (16 Mio. Pixel) |
| K3 | 14.3 Cover | ETag in Anführungszeichen; Antwort von POST/DELETE `{v, serie_id, cover_stand, cover_quelle}`; DELETE ohne eigenes Cover ist kein Fehler; Tag-Suche probiert höchstens `COVER_SUCHE_DATEIEN_MAX` (5) Dateien je Eintrag |
| K4 | 3 `hello.faehigkeiten` | Reihenfolge ist ohne Bedeutung (Code hängt in Bau-Reihenfolge an) |
| K5 | 14.10 | Hörkopie-Zeitgrenze 90 min nach Messung (40× Echtzeit auf dem QNAP) |

## Runde 13 (12.11., weitere Durchsicht, von Tobias eingebracht: „ein paar Änderungen hab ich noch“)

| Nr. | Punkt | Umsetzung (PL) |
|---|---|---|
| X13 | Zuordnen ohne Countdown: Ziel vorab am Handy festlegen | Tonies und Karten werden **nicht beschrieben** (die Box liest nur die Kennung). Umsetzung als **Warteschlange in HA**: „Nächster neuer Tobie auf <Box> spielt …“ (oder „auf irgendeiner Box“). Legt jemand dort einen unbekannten Tobie auf, ordnet HA ihn sofort zu (Name gleich mit, überspringbar) und meldet es. Kein Zeitlimit; Eintrag in der Warteschlange lässt sich abbrechen; nur unbekannte Tobies, nie bekannte umhängen. Der bisherige Lernmodus mit Countdown bleibt als Weg für Admins in „Technik“, für den Alltag ersetzt die Warteschlange ihn. Nur HA, keine Box-Änderung. |
| X14 | Player: Sperre gegen Kinderfinger | Knopf **„Sperren“** in der Player-Vollansicht: sperrt alle Bedienelemente, großes Cover bleibt; Entsperren durch langes Drücken (ca. 2 s) auf ein Schloss-Symbol. Die Geschwindigkeit wandert aus der Hauptzeile ins „⋯“ des Players. |
| X15 | „Technik“ übersichtlicher | Unterseiten statt aufklappbarer Abschnitte, z. B. **Boxen** (Zustand, Akku, Sync), **Speicher und Netz** (NAS, Eingang, Hörkopien, Papierkorb), **Liste und Sicherung** (Stände, Export), **Meldungen** (Protokoll mit Codes), **Einstellungen**. Listenmuster X10. |
| X16 | Suche: Vorschläge, Tobies zuerst | Beim Tippen Vorschläge (Autovervollständigen); **Tobies stehen oben**, mit dem, was sie gerade spielen; danach Serien, Folgen und Lieder. |
| X17 | Tonale Knöpfe | Sekundäre Knöpfe ohne Rahmen, getönter Hintergrund `--primary-soft`, Schrift `--primary-ink` (Kontrast ≥ 4,5:1 in allen Themes prüfen). |
| X18 | Aktiver Reiter als Pille | Statt Linie: abgerundeter Hintergrund (`--primary-soft`) hinter dem Symbol des aktiven Reiters. |
| X19 | Reiterleiste schwebend/Glas | Leicht durchscheinender Hintergrund aus Tokens (hell und dunkel) mit `backdrop-filter: blur(12px)`, ohne harte Linie; Rückfall ohne `backdrop-filter` mit deckendem Hintergrund; Kontrast der Beschriftung gegen den ungünstigsten Inhalt dahinter sichern. |

## Runde 14 (12.11., weitere Durchsicht, von Tobias eingebracht)

| Nr. | Punkt | Umsetzung (PL) |
|---|---|---|
| X20 | Bruch zwischen Bibliothek (digital) und Tobies (physisch) | **Tobias (Runde 14): Variante c „Ausgangspunkt ist immer der Tobie“** – erst die Figur, dann wählen, was sie spielt. Wird als eigene kleine Vorschau gezeigt, bevor sie in Design und Prototyp kommt. Früherer Vorschlag PL (Variante a, verworfen): Nach dem Hochladen und auf jeder Serien-/Playlist-Seite ist **„Einem Tobie geben“** die erste Aktion: wählt einen bekannten Tobie oder legt einen Eintrag in der Warteschlange an („nächster neuer Tobie auf <Box>“, X13). Auf der Tobies-Seite umgekehrt „Ziel wählen“ direkt mit Bibliothek-Suche. Der Reiter Tobies bleibt (Figuren verwalten). |
| X21 | Status (Start) und Diagnose (Technik) getrennt | Tipp auf eine Box-Karte auf Start öffnet die **Box-Detailseite**: für alle Akku, Laden, online, was läuft; für Admins darunter die Technik-Details dieser Box (dieselbe Unterseite wie „Technik › Boxen › <Box>“). |
| X22 | Zeiteingabe mit Auswahllisten | `<input type="time">` (System-Zeitwähler) für Leise-Zeiten und Gute Nacht, 5-Minuten-Schritte. |
| X23 | „Mehr zeigen“-Knopf in langen Listen | Endloses Nachladen beim Scrollen (IntersectionObserver), Knopf „Mehr laden“ bleibt als Rückfall für Tastatur und Screenreader; Ansage über `aria-live`. |
| X24 | Breite Bildschirme | Ab 900 px **Seitenleiste links** (wie Musik-Apps) statt Kopfleiste; Inhalt nutzt die volle Höhe; Player-Leiste unten über die Inhaltsbreite. |
| X25 | „⋯“ in Zeilen löst versehentlich aus | „⋯“ deutlich abgesetzt (eigene 44 × 44-Fläche mit Abstand und Trennung zur Zeilenfläche), Antippen öffnet nur ein Menü, nie eine Aktion direkt; Zeilenfläche endet vor dem „⋯“. |
| X26 | Leise-Zeiten schwer zu verstehen | **(Tobias)** Besser visualisieren; ersetzt die frühere Festlegung „Wochenplan-Grafik später“ (Frage 6). PL: **Wochenansicht als Zeitleisten** – je Wochentag eine Leiste 0–24 Uhr mit farbigen Abschnitten „leiser“ und „stumm“ (Farben aus Tokens, dazu Muster/Beschriftung, nicht nur Farbe), Markierung „jetzt“, darüber ein Satz „Jetzt: leiser bis 7:00“. Tipp auf einen Abschnitt öffnet ihn zum Bearbeiten (Zeitwähler X22, Tage, Art), „+ Leise-Zeit“ legt eine neue an. Zeiten über Mitternacht laufen sichtbar in den nächsten Tag. Gute Nacht bleibt eine eigene Karte darüber. |

## Runde 15 (12.11., Umbau der Architektur, von Tobias vorgegeben)

| Nr. | Punkt | Umsetzung (PL) |
|---|---|---|
| X27 | **Startseite = Schaufenster für Inhalte** | Keine Box-, Admin- oder Upload-Blöcke mehr. Kopf mit Begrüßung nach Tageszeit („Guten Morgen“) und kleinen runden Symbolen rechts (Technik nur für Admins). **Schnellzugriff-Raster** 2×3 (meist gehört bzw. Favoriten). Reihen: **„Am Handy weiterhören“** (Stufe A-2), **„Zuletzt auf den Boxen gehört“** (Stufe B), **„Neu hinzugefügt“** (Stufe A), **„Favoriten / Empfehlungen“** (Stufe B). Bis die Daten da sind, fehlt die jeweilige Reihe; das Raster füllt sich in Stufe A mit zuletzt hinzugefügten bzw. zuletzt zugeordneten Einträgen. |
| X28 | **Neuer Reiter „Geräte“ statt „Mehr“** (Lautsprecher-Symbol). Reiter: Start · Bibliothek · Tobies · Geräte | Inhalt: Status-Karten der Boxen (Akku, WLAN, was läuft; Tipp → Box-Detailseite X21), **Karte „Neuer Tobie aufgelegt“ nur hier** (dazu ein Punkt am Reiter „Geräte“, damit sie nicht übersehen wird), darunter **Gute Nacht und Leise-Zeiten** (X26). „Gehört“ (Stufe B, Rangliste je Box) wandert als Abschnitt in „Geräte“. „Mehr“ entfällt. |
| X29 | **Hinzufügen in die Bibliothek** | Großer Knopf und Upload-Zusammenfassung verschwinden vom Start. „+“ als deutliches Symbol im Kopf der Bibliothek; laufende Uploads als dezentes Band oben in der Bibliothek. Hochladen bleibt Alltag (alle Benutzer). |
| X30 | Folgen für frühere Entscheidungen | X1 (vier Reiter, „Mehr“) und X21 (Box-Karte auf Start) werden durch X27/X28 ersetzt; Box-Detailseite bleibt, erreicht über „Geräte“. Abkürzung „Abends“ auf dem Start entfällt (2 Taps über „Geräte“). |

## Runde 16 (12.11., Rückmeldung zu Prototyp v7 und Vorschau X20)

| Nr. | Entscheidung (Tobias) |
|---|---|
| X20 | **Angenommen:** Reiter Tobies wie in der Vorschau `x20_tobie_zuerst.html` („super“), Variante c. Dazu: a) Link „Einem Tobie geben …“ bleibt in der Bibliothek; b) bei einer einzelnen Folge steht im Regal auch der Serienname; c) Gute Nacht beim Tobie als eigene Zeile; d) nach dem Zuordnen einige Sekunden „Rückgängig“. |
| X12a | Hochlade-Kachel „Neue Playlist“ entfällt; nach dem Hochladen „Zur Playlist hinzufügen“ (Upload-Wunsch `ziel=playlist` entfällt). |
| X13a | Lernmodus mit Countdown nur noch für Administratoren (`lernmodus/start` wieder `admin`; Vertragsänderung mit A0-Q). |
| X22a | Gute Nacht bleibt eine Dauer mit Schnellwahl; der Zeitwähler gilt nur für Leise-Zeiten. |
| X27a | „Am Handy weiterhören“ und „Neu hinzugefügt“ nur auf dem Start, nicht mehr in der Bibliothek. |
| X31 | Kein Spalt zwischen Mini-Player und Reiterleiste: der Player sitzt bündig auf der Leiste. |
| X20e | **(Tobias)** „Einem Tobie geben …“ auch im „⋯“-Menü von einzelnen Folgen, Liedern und Playlist-Einträgen. |
| X20f | **(Tobias)** Neben „Gespielt von“-Chips ein kleines „+“, das zur Tobie-Auswahl führt (zweiter Tobie für denselben Eintrag). |
| X32 | **(Tobias)** Segment-Umschalter sauber: gleich breite Segmente, Text mittig, getönte Spur ohne Rahmen, Auswahl als Pille innerhalb der Spur; einheitlich für alle Umschalter. |
| X33 | Animationen fehlen im Prototyp (Tobias: „kommen Animationen im fertigen?“) | **(PL)** Ja, festgelegt und schon im Prototyp gezeigt: Bewegungs-Tokens (kurz ~150 ms, mittel ~250 ms, lang ~350 ms, eine Standard-Kurve); Blätter gleiten von unten herein und hinaus, Hintergrund blendet; beim Wischen folgt das Blatt dem Finger und federt zurück, wenn nicht weit genug; Mini-Player fährt zur Vollansicht auf und zu; Meldungen gleiten herein und hinaus; Seitenwechsel mit kurzem Überblenden; Pille im Segment-Umschalter und am aktiven Reiter gleitet. Bei „reduzierte Bewegung“ (`prefers-reduced-motion`) nur Überblenden oder sofort. |
| X34 | Animation zu wenig (Tobias: Player erscheint abrupt, beim Mini-Player ebenso; Vorbild Apple) | **(PL)** Bewegung nach Apples Human Interface Guidelines und dem Vorbild Apple Music: **Feder-Kurven** statt fester Kurven (über CSS `linear()` nachgebildet, Dauer bis ca. 500 ms; ersetzt die 400-ms-Grenze aus X33); **Cover wandert** vom Mini-Player in die Vollansicht und zurück (View Transitions API, Safari ab 18 / WKWebView; Rückfall: Transform-Animation); Mini-Player **federt herein**, wenn etwas zu spielen beginnt, Cover in der Liste gibt kurz Rückmeldung; **Blatt-Darstellung wie iOS**: die Seite dahinter wird leicht kleiner und bekommt runde Ecken; **Druck-Rückmeldung** (Knöpfe, Kacheln, Zeilen leicht kleiner beim Drücken); **Abspiel-Anzeige** (kleine Balken) bei dem, was gerade läuft; Cover der Serie wächst beim Öffnen der Serienseite in den Kopf (View Transition). „Reduzierte Bewegung“ bleibt: nur Überblenden. |
| X34a | Offen aus X34 (PL) | Im echten HA zu prüfen, bevor A6/A8b darauf bauen: View Transitions mit Elementen im **Shadow-DOM** des Panels (sonst FLIP-Rückfall), iOS-Blatt-Effekt nur auf den Panel-Inhalt (nicht HA-Kopfleiste), Verhalten in der Companion-App am iPhone. Kleiner Test im Testpanel `/tobibox-neu` vor A6. |

## Stand 13.11.: Prototyp v8 abgeschlossen

**(Tobias, 13.11.)** Bewegung X34 „schaut gut aus“. Design `docs/designs/ha-oberflaeche.md` mit Runden 12–16 (X1–X34) und Prototyp v8 gelten als Grundlage für den Bau der Seite. Vor A6: (1) Vertragsänderungen A0-Q (Warteschlange X13, Lernmodus nur Admin X13a) zur Freigabe, (2) Test X34a im echten HA, (3) Goldfisch-Review der seit Rev. 5 stark geänderten Abschnitte.

## Runde 17 (13.11., Goldfisch-Review v8 und Freigabe A0-Q)

**(Tobias: „Alles ok“)** – alle Empfehlungen zu den Fragen aus `review_goldfisch_v8.md` angenommen; A0-Q gilt als freigegeben (Tobias kann widersprechen).

| Nr. | Entscheidung |
|---|---|
| R17-1 (N1) | Cover-Flug über **FLIP als Standardweg** (sicher im Shadow-DOM); View Transitions nur, wo nachweislich wirksam. iPhone-Test X34a prüft nur noch das Gefühl. |
| R17-2 (N5) | Eigene Seitenleiste erst ab ca. **1100 px Panelbreite** (nicht Fensterbreite); darunter Reiter (unten bzw. oben). |
| R17-3 (N6) | Umhängen ohne Rückfrage; Meldung nennt altes und neues Ziel mit „Rückgängig“; auf der Tobie-Seite bleibt eine Zeile „Vorher: …“. |
| R17-4 (N15) | Während eines Uploads darf „Bildschirm anlassen, bis es fertig ist“ in der Fortschrittskarte stehen (echter Zustand). |
| R17-5 (N11) | Optionales Namensfeld schon bei „Später auflegen“. |
| R17-6 (N21) | Zusätzlich zum Punkt an „Geräte“ kurze Meldung auf jeder Seite „Neuer Tobie auf <Box> – Zuordnen“. |
| R17-7 (N19) | „Gehört“ als eigene Unterseite hinter einer Zeile in „Geräte“. |
| R17-8 (N4) | A-1 in drei Abnahmen: **A-1a** Lesen und Abends, **A-1b** Tobies, **A-1c** Hinzufügen und Cover; Bewegung als eigenes Paket nach dem Test im echten HA. |
| A0-Q | Freigegeben: Warteschlange (Befehle 47–49, Thema `warteschlange`, Fehler `warteschlange_voll`/`_doppelt`, Fähigkeiten `warteschlange`, `zuordnung_rueckgaengig`, `als_neu` bei `zuordnung/remove`), Lernmodus 18–20 nur Admin. |

Alle übrigen Befunde N1–N29 werden nach den Vorschlägen des Reviews eingearbeitet.
| X34b | **(Tobias, 13.11.)** Bewegungstest X34a im echten HA entfällt. Gebaut wird gleich mit FLIP als Standardweg (R17-1); funktioniert etwas im echten HA nicht wie gedacht, greift der Rückfall (Überblenden). Abschnitt h) im Testpanel bleibt für später. |
| R17-9 | **(Tobias, 13.11.)** Die neue Seite heißt nicht `/tobibox-neu`: Die alte Seite ist noch nicht im Alltagsbetrieb. Die neue Seite übernimmt **`/tobibox`** („Tobi Box“ in der Seitenleiste); die alte Komponente bleibt nur noch eingebettet in „Technik“ (für Funktionen, die die neue Seite noch nicht hat), ohne eigenen Seitenleisten-Eintrag. Testpanel unter `/tobibox-test`. Bis zur Abnahme A17 bleibt die Seite nur für Administratoren. |
| K6/K7 | **(Tobias, 13.11.) freigegeben:** K6 Feld `vorher` (vorheriges Ziel, mit Zeitpunkt) an `zuordnung/list`, damit „Vorher: …“ auf allen Geräten steht; K7 optionales Feld `name` bei `warteschlange/set`, das beim Zuordnen als Name des Tobies übernommen wird. Beide additiv. |
