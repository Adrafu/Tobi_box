# Altersfilter, Paket AF0: Entwurf der Vertragsänderungen

Stand 23.11. Grundlage: `docs/designs/altersfilter.md` (Rev. 2, Abschnitte 3 und 4) und `docs/egm/altersfilter/resolve.md`.
**Von Tobias freigegeben am 23.11.** („Ja, freigeben“) und in `docs/protocol/ha-websocket-v1.md` und `docs/data-model.md` übernommen. Die Diffs zeigen den Stand vor der Übernahme.

| Datei | Inhalt |
|---|---|
| `ha-websocket-v1.md` | volle Kopie von Vertrag W mit den Änderungen |
| `ha-websocket-v1.diff` | `diff -u docs/protocol/ha-websocket-v1.md docs/egm/altersfilter/vertrag_entwurf/ha-websocket-v1.md` |
| `data-model.md` | volle Kopie des Datenmodells mit den Änderungen |
| `data-model.diff` | `diff -u docs/data-model.md docs/egm/altersfilter/vertrag_entwurf/data-model.md` |

`mqtt-v1.md`, die Box und der Sync bleiben unverändert; der Kopf-Eintrag sagt es. Die Version bleibt 1, alles ist additiv. Die Nummer 66 war frei (die letzte vergebene war 65).
Die Diffs enthalten nur Einschübe; in wenigen Zeilen (Aufzählungen) wird ein Satz am Zeilenende oder eine Nummer ergänzt, sonst nichts entfernt.

## Was geändert ist

**Vertrag W (`ha-websocket-v1.md`)**

| Stelle | Änderung | Design |
|---|---|---|
| Kopf | Eintrag „Änderung 23.11. (Altersfilter, Paket AF0 …)“ | 4 |
| 2.1 | Rechte: Nr. 66 bei **alltag**; Satz „Nr. 66 seit dem 23.11.“ | 4.3 |
| Übersicht 3 | Zeile 66 `serie/alter_setzen`, alltag, idempotent ja, MQTT –; Schlusssatz | 4.3 |
| 1 `hello` | Fähigkeit `alter` in der Aufzählung der Fähigkeiten | 4 |
| 14.1 | Zeile `alter` (Eingabe `alter`, Befehl 66; Ausgabefelder ohne Fähigkeit) | 4 |
| 14.2 Kurzform | Felder `alter_ab` (Eintrags-Alter mit Regel und „gültiger Shop-Wert“) und `alter_hand`; Hinweis, dass das Folge-Objekt sein `alter_ab` (Shop-Alter) behält | 2, 4.1 |
| 14.2 `serien/list` | Eingabe `alter` (int 0 bis 18 oder `"ohne"`, ≤ X, „und“, strenges Schema, `invalid_format`) | 4.2 |
| 3.2 Nr. 26 | `folge/verschieben` nimmt `alter_hand` nicht mit | 3.3 |
| 3.2 Nr. 27 | `serien/zusammenfuehren`: Ziel übernimmt `alter_hand`, wenn es keins hat | 3.3 |
| 3.15 Nr. 66 (neu) | `tobibox/serie/alter_setzen`: Eingabe, Wirkung, Ausgabe, Ereignis, Fehler, Recht alltag (auch Überraschungs-Serie), idempotent | 4.3 |

**Datenmodell (`data-model.md`)**

| Stelle | Änderung | Design |
|---|---|---|
| Kopf | Eintrag „Änderung 23.11. (Altersfilter, Paket AF0 …)“ | 4.4 |
| 5 `serie.json` | Zeile `alter_hand` (int 0 bis 18, optional, nur von Menschen und beim Zusammenführen übernommen; ungültig = fehlt; Box ignoriert; nicht im `stand`) | 3.1, 4.4 |
| 5 (Box-Ignorierliste) | `alter_hand` ergänzt | 3.1 |

Abschnitt 1.4 (unbekannte Felder) bleibt unverändert; er gilt schon.
