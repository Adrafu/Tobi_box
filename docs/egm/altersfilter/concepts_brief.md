# Altersfilter in der Bibliothek: Concepts Brief (EGM Schritt 1)

Stand 23.11. · Anlass: Tobias möchte, dass Eltern die Bibliothek der HA-Seite nach dem Alter der Kinder filtern
können.

## 1. Problem

Die Bibliothek hat 341 Einträge. Eltern suchen „Was passt für ein Kind mit 4 Jahren?“. Heute gibt es dafür keinen
Filter. Eine Altersangabe gibt es nur je Folge, nur aus der Online-Suche und nur auf der Serien-Seite.

## 2. Was schon feststeht (Bestand, geprüft am 22./23.11.)

- **Feld `alter_ab`** (int 0 bis 18, „ab X Jahren“) gibt es **je Folge** im Store `tobibox.online`
  (`docs/data-model.md`, 5b: `serien.<id>.folgen.<f>`). Einzige Quelle: die **Tonie-Shopseite** (`ageMin`), nur bei
  sicherem Tonie-Treffer (Design Online-Suche 4.2). Apple liefert kein Alter.
- Die Seite zeigt es nur in `serie/get` an der Folge (Vertrag W, 3.2; `serie.js`: „ab 4“). Die Serie-Kurzform von
  `serien/list` hat **kein** Alter.
- **Von Hand** gibt es heute kein Alter. „Hand“ heißt bei der Online-Suche nur: in einer Übernahme gewählt
  (`hand`, Design Online-Suche 6.1).
- Die Bibliothek sucht, filtert, sortiert und blättert **im Backend** (`serien/list`, Päckchen von 60, `gesamt`;
  `bibliothek.py`). Ein Filter nur in der Seite geht deshalb nicht.
- Für die Kinder gibt es im Datenmodell kein Alter und kein Geburtsdatum (und das bleibt so, siehe A4).

**Messung in der echten Bibliothek (23.11., nur lesend über `homeassistant.local`):**

| | Anzahl |
|---|---|
| Einträge / Folgen | 341 / 820 |
| Einträge mit mindestens einer Folge mit Alter | 85 (25 %) |
| Einträge, bei denen alle Folgen ein Alter haben | 40 |
| Einträge ganz ohne Alter | 256 (75 %) |
| Folgen mit Alter | 124 |
| Werte (Folgen) | 1: 6, 3: 51, 4: 12, 5: 35, 6: 12, 7: 4, 8: 2, 10: 2 |
| Einträge mit verschiedenen Werten | 6 von 25 mit mindestens zwei Werten, größte Spanne 2 Jahre |
| nach Art (mit Alter / ohne) | Hörspiel 58 / 194, Hörbuch 11 / 38, Musik 13 / 22, Geschichte 3 / 2 |

Folge: Ohne Eingabe von Hand bleibt der Filter für drei Viertel der Bibliothek blind.

## 3. Entscheidungen aus dem Brainstorm (Tobias, 23.11.)

| Nr. | Frage | Antwort |
|---|---|---|
| A1 | Form der Wahl | **„Für ein Kind mit X Jahren“**: eine Zahl wählen; gezeigt wird alles mit „ab X“ oder jünger |
| A2 | Einträge ohne Alter | Die Alterswahl hat **einen eigenen Eintrag „ohne Altersangabe“**. Er ist **eine Wahl von vielen** (Alle, 1, 2, …, ohne Altersangabe), genau eine gilt. „Ohne Altersangabe“ zeigt nur die Einträge ohne Alter (gut zum Nachtragen). Bei einer Zahl erscheinen Einträge ohne Alter **nicht** |
| A3 | Mehrere Folgen mit Alter | **Die jüngste Angabe zählt**: Der Eintrag passt, wenn mindestens eine Folge passt (Eintrags-Alter = kleinster Wert der Folgen) |
| A4 | Alter von Hand | **Ja, je Eintrag**: ein Feld „ab … Jahren“ am Eintrag, gilt für den ganzen Eintrag und geht vor den Shop-Werten |
| A5 | Wer darf es setzen | **Wer bearbeiten darf** (wie Art, Name, Cover; Recht „alltag“), nicht nur Administratoren |
| A6 | Anzeige auf der Serien-Seite | **Oben am Eintrag** „ab 4“ (von Hand); bei den Folgen bleibt der Shop-Wert stehen, wo es einen gibt. Der Filter nimmt den Wert von Hand |
| A7 | Umfang | **Nur Bibliothek**, nicht Suche, nicht Start |
| A8 | Merken | **Nicht merken**, wie die anderen Filter (nach dem Neuladen ist die Wahl weg) |

## 4. Grenzen

- Nur HA-Seite und Integration. Box, `mqtt-v1.md` und Sync bleiben unverändert. Die Box ignoriert ein neues Feld in
  `serie.json` (`data-model.md`, 1.4).
- Kein Alter und kein Geburtsdatum der Kinder im Repo oder im Datenmodell (A1 braucht es nicht).
- Neue Felder und Eingaben sind **Vertragsänderungen** (`docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`):
  Entwurf als Diff in diesem Ordner, Übernahme erst nach Tobias' Ja (wie OS0).
- Die Online-Suche bleibt, wie sie ist: Sie schreibt weiter `alter_ab` je Folge in ihren Store und überschreibt nie
  einen Wert von Hand.

## 5. Offen für den Entwurf

- Wo das Alter von Hand liegt (`serie.json` wie `art`, oder Store).
- Welche Zahlen die Wahl anbietet (fest, z. B. 1 bis 12, oder nur vorkommende Werte).
- Wie man den Wert von Hand wieder löscht und was dann gilt (Shop-Wert).
- Ob das Eintrags-Alter in der Kurzform auch in der Liste zu sehen ist (Kachel, Zeile).
