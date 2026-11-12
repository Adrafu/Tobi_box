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
