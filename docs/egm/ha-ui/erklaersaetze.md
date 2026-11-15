# Erklärende Sätze der Seite (Liste zu AM16, 15.11.)

Regel (Tobias, 15.11.): Die Seite erklärt sich selbst, keine beschreibenden Sätze. Vorbild Spotify.
Grundlage: alle Sätze aus `frontend/texte.js`, die auf der Seite als eigene Zeile stehen.
Der Koordinator schlägt je Satz vor: **weg**, **kürzer** oder **bleibt**. **Tobias, 15.11.: „Alles so umsetzen“ (AM17).**

## Vorschlag: weg

Diese Sätze erklären die Bedienung oder wiederholen, was man ohnehin sieht.

| Bereich | Schlüssel | Satz |
|---|---|---|
| Serienseite | `PLAYER.knopf.hinweis` | Das spielt hier am Handy oder Computer, nicht auf der Box. (schon entschieden) |
| Serienseite | `SERIE.einzeln.*`, `.schluss` | Das ist ein einzelnes Lied. Es steht für sich … Du kannst einem Tobie das zu spielen geben. |
| Serienseite | `SERIE.art.satz` | Die Art wurde aus den Tags vorgeschlagen. Hier kannst du sie ändern. |
| Serienseite | `SERIE.stimmt_nicht.folge` | Gehört nur eine einzelne Folge woandershin? Tippe bei der Folge auf „⋯“ … |
| Cover | `COVER.satz`, `COVER.satz_schneiden` | Wähle ein Foto. Am Handy kannst du … / Verschiebe das Foto mit dem Finger … |
| Player | `PLAYER.voll.stelle_gemerkt` | Die Stelle wird gemerkt, auch für das andere Gerät. |
| Player | `HOERPROBE.fertig` | Die Hörprobe ist fertig. Tippe auf Reinhören. (nur noch „Die Hörprobe ist fertig.“) |
| Tobies | `TOBIE.name_hinweis` | Du kannst das überspringen. |
| Tobies | `TOBIES.queue.warte_satz` | Kein Zeitlimit. Du musst die Seite nicht offen lassen. |
| Geräte | `ABENDS.gute_nacht.text` | Lege den Gute-Nacht-Tobie auf. Dann läuft ein Timer … |
| Geräte | `LEISE.gilt_fuer` | Gilt für {tage}. Tage abwählen, wenn es nur für einzelne gelten soll. |
| Hinzufügen | `HINZU.blatt.sortier_du` | Ich lese die Angaben in den Dateien (Album, Interpret, Titel) … |
| Hinzufügen | `HINZU.blatt.zusammen` | Die Dateien bleiben zusammen. Einsortiert wird, wenn alle {anzahl} da sind. |
| Hinzufügen | `HINZU.erledigte.geraet` | Das gilt nur auf diesem Gerät. |
| Technik | `TECHNIK.korb.satz` | Legt jemand anderes etwas in den Papierkorb, sehen Administratoren einen Punkt … |
| Technik | `TECHNIK.korb.neu.hilfe` | Antippen holt einen Eintrag zurück. „Letzte Stunde zurückholen“ steht unten. |
| Technik | `TECHNIK.liste.staende.text` | Die letzten Stände der Liste. Einen Stand kannst du ansehen und zurückspielen. |
| Technik | `TECHNIK.aufraeumen.*_text` | Schaut nach, ob auf dem NAS … / Sucht die Bilder … / Versucht es noch einmal … |

## Vorschlag: kürzer

Leere Zustände sagen nur noch, dass nichts da ist; der Weg ist der Knopf daneben.

| Schlüssel | heute | neu |
|---|---|---|
| `LEER.start.satz` | Noch nichts da. Tippe in der Bibliothek auf „+“. | Noch nichts da. (mit Knopf „Hinzufügen“) |
| `LEER.bibliothek.satz` | Noch nichts da. Tippe auf „Hinzufügen“. | Noch nichts da. |
| `LEER.filter.satz` | Nichts gefunden. Nimm einen Filter weg. | Nichts gefunden. |
| `LEER.tobies.satz` | Noch keine Tobies. Lege einen Tobie auf eine Box, dann erscheint er unter „Geräte“. | Noch keine Tobies. Leg einen auf eine Box. |
| `LEER.gehoert.satz` | Noch nichts gehört. Sobald eine Box spielt oder jemand reinhört, steht es hier. | Noch nichts gehört. |
| `SUCHE.weitere` | … und {anzahl} weitere. Genauer suchen hilft. | … und {anzahl} weitere. |
| `SEITE.verbindung_weg.text` | Die Ansicht wird von selbst aktuell, sobald die Verbindung wieder da ist. | (nur die Überschrift „Keine Verbindung“) |
| `ABENDS.leise.leer` | Keine Leise-Zeiten. Die Box spielt immer in normaler Lautstärke. | Keine Leise-Zeiten. |
| `ABENDS.meldung.gespeichert` | Gespeichert. Die Boxen bekommen es gleich. | Gespeichert. |

## Vorschlag: bleibt

* **Folgen vor dem Löschen, Verschieben, Zusammenführen, Liste neu ausrollen, Papierkorb leeren** (`SERIE.papierkorb.*`, `SERIE.verschieben.*`, `SERIE.zusammen.*`, `TOBIES.vergessen.satz`, `TECHNIK.liste.*`, `TECHNIK.korb.leeren_text` …): Sie sagen, was danach anders ist (zum Beispiel welche Tobies dann nichts mehr spielen). Das kann man nicht sehen, bevor man tippt.
* **Rückmeldungen nach einer Aktion** („Fertig: … spielt jetzt …“, „… ist im Papierkorb.“, „Abgebrochen. Es wurde nichts einsortiert.“).
* **Gründe und Hinweise vom Einsortieren** (`GRUENDE.*`, `HINWEISE.*`, „Bitte kurz ansehen“): Sie sagen, warum etwas unsicher ist.
* **Vorschau beim Hochladen** („3 Dateien → neues Hörbuch …“): von Tobias in Runde 8 so gewünscht.
* **Zustände der Boxen und Hörproben** (`STATUS.*`, `HOERPROBE.vorbereitung`, `HOERPROBE.keine_datei`, `FEHLER.browser_spielt_nicht`), **Warnbänder in Technik**, **„Bildschirm anlassen, bis es fertig ist.“** beim Hochladen, **Zeile unter dem großen Knopf** („Schlaflieder · ab 0:24“).
* Unterzeilen der Technik-Einträge („Zustand, Sync und Meldungen je Box“): wie in den Einstellungen von iOS, keine Erklärung der Bedienung.

## Unbenutzt (fliegen ohnehin raus)

`HOERPROBE.keine_datei_admin`, `FEHLER.hoerkopie_wartet`, `HINZU.blatt.wohin_nichts`, `KACHELN.playlist.satz`.
