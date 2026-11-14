# Vorschlag: Sammelordner im Eingang (Vertrag W, 11.3) – Befund AC1

Stand 14.11., Projektleitung. **Noch nicht im Vertrag**; gilt erst nach Tobias’ Freigabe.

## Anlass

Ein Ordner mit vielen Büchern, je Buch ein Unterordner (z. B. eine gekaufte Sammlung mit 1812 Dateien), kam
über den NAS-Eingang. Zwei Dateien in zwei Büchern lassen sich nicht abspielen. Ergebnis heute: **nichts** wird
einsortiert, der ganze Ordner bleibt „blockiert“.

Das ist nach heutigem Vertrag richtig: 11.3 bildet Gruppen je Album über den **ganzen** Eintrag; Dateien ohne
Album-Tag sind **eine** Gruppe je Eintrag. Tragen die Bücher keinen oder denselben Album-Tag, ist der ganze Ordner
eine Gruppe, und 11.10 hält bei einer kaputten Datei die ganze Gruppe zurück. Ohne die zwei kaputten Dateien
würde der Ordner sogar **eine** Folge mit über 1000 Tracks.

## Vorschlag

Neuer Begriff **Teil**: In einem Ordner-Eintrag ist jeder **Unterordner der ersten Ebene** ein Teil. Dateien direkt
im Eintrag gehören zum Teil „Eintrag selbst“. **Ausnahme:** Ein Unterordner, dessen Name nur eine CD- oder
Disc-Angabe ist (`CD1`, `CD 2`, `Disc 1`, `Disk 2`, Groß/klein egal), ist kein eigener Teil, sondern gehört zum
übergeordneten Teil (damit `Hörbuch X/CD1/`, `CD2/` eine Folge bleiben).

11.3 neu:

* **Datei mit `album`, im Ordner-Eintrag:** Gruppe = (Eintrag, **Teil**, `norm(album)`). Dateien desselben Albums
  in `CD1/` und `CD2/` sind weiter eine Gruppe (Ausnahme oben).
* **Datei ohne `album`, im Ordner-Eintrag:** Alle solchen Dateien **eines Teils** bilden eine Gruppe
  (`tags_fehlen`). Anzeigename bei mehreren Dateien: Name des **Teils** (Unterordner), sonst wie bisher.
* Lose Dateien in `eingang/`: unverändert.

11.5 Nr. 5 neu: Liegt die Gruppe in einem Teil-Unterordner, ist der Ordnername für die Serie der Name des
**Teils**, sonst der Name des Eintrags (`serie_aus_ordner` wie bisher).

11.10 bleibt wörtlich; durch die neuen Gruppen hält eine kaputte Datei nur noch **ihr Buch** zurück, der Rest wird
einsortiert, Status `teilweise`, die Hinweise nennen die Dateien.

Neuer Testfall **T21**: Ordner `Sammlung/` mit `Buch A/` (3 Dateien ohne Tags), `Buch B/` (2 Dateien, eine kaputt),
`Buch C/CD1/`, `Buch C/CD2/` (gleiches Album) → Serie `Buch A` mit einer Folge (3 Tracks), Serie aus Album für
Buch C mit **einer** Folge aus CD1 und CD2, `Buch B` bleibt im Eingang; Eintrag `teilweise`.

## Was sich für bestehende Fälle ändert

* Ein Hörspiel mit Unterordnern **je Folge** und gleichem Album-Tag in allen (`Serie/Folge 1/`, `Serie/Folge 2/`)
  wird künftig zu **mehreren** Folgen (eine je Unterordner) statt einer. Das ist meist richtiger.
* T1–T20 bleiben gültig (keiner hat Unterordner außer CD1/CD2).
* Nicht betroffen: Upload (Gruppen kommen dort aus `gruppe`/`gruppe_anzahl`), Box, `mqtt-v1.md`, Datenmodell.

## Für den echten Ordner

Nach Freigabe, Umsetzung (Python, mit Tests) und HA-Neustart sortiert der nächste Durchlauf alle Bücher ein, die
heil sind; „Die Haferhorde – Volle Mähne!“ und „Felix – Briefe von Felix“ bleiben im Eingang, bis die kaputten
Dateien ersetzt sind. Jedes Buch wird eine eigene Serie mit dem Namen des Unterordners (oder aus den Tags), sofern
die Dateien keine besseren Angaben tragen.
