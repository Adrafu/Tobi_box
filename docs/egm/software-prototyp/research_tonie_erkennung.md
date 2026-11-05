# Recherche: Tonie-Figur automatisch erkennen

Stand: 2026-11-05. Recherche nur per Websuche, ohne Repo-Clone. Die Hauptquelle (Wiki der toniebox-reverse-engineering-Org) war nicht abrufbar (404). Vieles stammt aus Forenbeiträgen der Community, nicht von Hersteller oder NXP.
Markierung: **[belegt]** = Quelle gefunden, **[offen]** = nicht belegt.

## Kurzantwort

Annahme **weitgehend bestätigt**: Die UID ist eine Seriennummer pro Figur. Auf dem Chip ist keine lesbare Figuren-Kennung bekannt. Eine öffentliche Liste "UID -> Figur" wurde nicht gefunden. Der Beleg dafür ist nur indirekt (siehe 1 und 3).

## 1. Daten auf dem Chip

- UID beginnt bei Originalen immer mit E0 04 03 50, die restlichen Bytes sind pro Chip eindeutig. **[belegt]** https://forum.revvox.de/t/ultimate-noob-guide/98/2
- Die Box verlangt Privacy Mode, die ersten drei UID-Bytes E0 04 03 und genau 8 Speicherblöcke. Sie liest die Blöcke 0x00 bis 0x08. **[belegt, Forum]** (gleiche Suche, Thread "Dump/privacy mode" u. a. https://forum.revvox.de/t/magic-slix-l-tags-from-rfidfriend-work-great/3314)
- Ein leeres, funktionierendes SLIX-L hat in den Blöcken 0-7 nur 00. **[belegt, Forum]** https://forum.revvox.de/t/magic-slix-l-tags-from-rfidfriend-work-great/3314
  Selbst selbstgebaute Tags ohne Inhalt funktionieren, also muss die Identität in der UID liegen und nicht im Speicher. Das ist ein **Indiz**, kein direkter Beweis, dass auch Originale keine Modellnummer im Speicher haben. **[offen]**: ein Dump eines Original-Tags mit Blockinhalt wurde nicht gefunden.
- Passwort/Auth: Das Passwort-Schema wurde in den Treffern nicht erklärt. **[offen]**

## 2. Wie die echte Toniebox erkennt

- Die Box fragt den Server mit der **rUID** an (UID in umgekehrter Byte-Reihenfolge, z. B. Tag E0:04:03:50:20:21:AD:68 -> Ordner 68ad2120, Datei 500304e0). **[belegt, Forum]** https://forum.revvox.de/t/codeword-groundhog-when-placing-custom-tags-with-teddycloud-content-assigned/2786
- Der Server liefert pro rUID die Audiodatei (TAF) oder bei Unbekanntem "Codeword Groundhog". Es ist also eine **Cloud-Suche nach UID**. Der Chip trägt keinen Titel. **[belegt, Forum]** (gleiche URL)
- TeddyCloud speichert die rUID pro Tonie in content.json (Feld cloud_ruid). **[belegt]** https://tonies-wiki.revvox.de/docs/tools/teddycloud/content-json/

## 3. TeddyCloud und tonies.json

- tonies.json hat pro Eintrag u. a. model, audio_id, hash. Die Datei wird aus einem GitHub-Repo erzeugt, das audio_ids sammelt. **[belegt]** https://tonies-wiki.revvox.de/docs/tools/teddycloud/tonies-custom-json/ , https://forum.revvox.de/t/audio-id-model-id-tonies-json/1515
- "Model ID" = ID der Figur selbst, "Audio ID" = ID des Inhalts. Bei Creative Tonies ändert sich die Audio ID, die Model ID bleibt. **[belegt]** https://forum.revvox.de/t/audio-id-model-id-tonies-json/1515
- Die automatische Zuordnung läuft über **audio_id/hash aus der Inhaltsdatei**, nicht über die UID. Fehlt audio_id/hash in tonies.json (bei Zusatzinhalten oft), gibt es keine automatische Zuordnung. **[belegt, Forum]** https://forum.revvox.de/t/how-to-get-audioid-and-hash-for-tap-file/1034 und https://forum.revvox.de/t/unknown-missing-tonies-in-tonies-json/457
- Folge: TeddyCloud kennt die Figur erst, **nachdem** die Box (oder TeddyBench) die Inhaltsdatei geholt hat. Nur aus der UID ist die Figur nicht bestimmbar. **[belegt als Folgerung, nicht wörtlich zitiert]**
- Eine Community-Datenbank "UID -> Figur" wurde nicht gefunden. **[offen]** Gäbe es sie, wäre sie rechtlich heikel (siehe 5).

## 4. Andere Wege

- **Offizielle Cloud/App (my.tonies.com):** Die inoffiziellen Bibliotheken zeigen Haushalte, Tonieboxen und Creative Tonies. Normale Figuren mit UID sind in der Doku nicht aufgeführt. **[belegt]** https://tonie-api.readthedocs.io/en/latest/Introduction.html ; ob die Konto-Figurenliste UIDs enthält, ist **[offen]**.
- **Artikelnummer/Barcode:** Auf Verpackung oder Figurenunterseite vorhanden **[unbelegt, aus allgemeiner Kenntnis]**. Der Barcode (EAN) sagt aber nichts über die UID. Ein Scan der Verpackung kann daher nur den Namen liefern, die Verknüpfung mit der UID müsste der Elternteil einmal herstellen (Scan, dann Figur auflegen).
- **Bilderkennung** (Kamera, Foto der Figur): denkbar, nur erwähnt, nicht geprüft. Aufwand hoch.

## 5. Recht / Nutzungsbedingungen (neutral)

- Die inoffiziellen Tonie-Cloud-Bibliotheken sagen selbst: nicht mit Boxine verbunden, "use at your own risk", API kann sich jederzeit ändern. **[belegt]** https://tonie-api.readthedocs.io/en/latest/Introduction.html
- Ob die AGB von tonies die Nutzung der inoffiziellen API erlauben, wurde **nicht geprüft** **[offen]**. Vor Einsatz die aktuellen AGB prüfen. Zugangsdaten gehören nie ins Repo.
- Passwort/Auth-Daten der Tags stehen unter der Regel aus CLAUDE.md (nie committen).

## Fazit für die Tobi Box

**Vollautomatische Erkennung ist nicht möglich.** Die UID ist eine Seriennummer, der Chip trägt (nach allem, was belegbar ist) keinen Titel, und eine öffentliche UID-Figur-Liste existiert nicht. Selbst TeddyCloud erkennt Figuren erst nach dem Inhalts-Download der echten Box.

**Geringster Aufwand, halbautomatisch:** Beim ersten Auflegen einer unbekannten UID fragt die Box den Elternteil einmalig nach Namen und Inhalt (z. B. kleines Web-Formular mit Eingabe oder Auswahl, optional Foto). Die Zuordnung wird lokal gespeichert (UID -> Name -> Audio). Danach läuft die Figur automatisch. Pro Figur ein einmaliger Schritt, bei einer Handvoll Figuren vertretbar.

**Vor einer Cloud-Lösung:** Tobias sollte mit einer echten Figur prüfen, ob das Konto bei my.tonies.com UIDs zeigt (offen), und die AGB lesen.
