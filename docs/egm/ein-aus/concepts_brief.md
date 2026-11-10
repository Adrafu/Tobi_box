# Ein- und Ausschalten: Concepts Brief (EGM Schritt 1)

Stand 10.11. · Grundlage: `brainstorm.md` (Antworten von Tobias), `research.md` (Fakten mit Quellen).
Ersetzt nach Annahme das ruhende EGM `docs/egm/start-am-lader/` (Teile davon fließen ein, siehe Abschnitt 6).

## 1. Problem

Die Box soll so schnell spielen wie eine Toniebox (unter 3 s vom Auflegen bis zum Ton), aber der Akku muss
einen Tag ohne Sockel tragen. Ein Raspberry Pi 3A+ kann nicht schlafen (`research.md` 2): Entweder er läuft
und braucht dabei fast so viel wie beim Spielen, oder er ist aus und braucht für den Start deutlich länger
als 3 s (`research.md` 3). Heute geht die Box nach 20 min Leerlauf ganz aus, und nur der Hauptknopf oder
das Andocken schaltet sie wieder ein.

## 2. Ziele und Grenzen (von Tobias, 10.11.)

| Punkt | Vorgabe |
|---|---|
| Wartezeit, wenn die Box bereit ist | **unter 3 s** vom Auflegen bis zum Ton |
| Wecken aus „ganz aus“ | Ein aufgelegter Tobie weckt die Box, **wenn machbar** (am Breadboard ausprobieren). Ziel 10 s bis zum Ton. Rückfall: Hauptknopf. |
| Ladetakt | Box steht **jede Nacht am Sockel**. Es zählt die Laufzeit pro Tag; Wochen im Schrank sind egal. |
| Nutzung | mehrmals täglich kurz, abends zum Einschlafen, unterwegs; tagsüber oft, aber nicht meistens am Sockel |
| Am Sockel | **immer bereit, auch nachts** |
| Ohne Sockel | **10 min** bereit nach dem letzten Hören, dann ganz aus |
| Stromsparen im Warten | Schalter (MOSFET) für Teile, die dunkel oder untätig Strom ziehen: **gleich einplanen** |

## 3. Konzept: drei Zustände

| Zustand | Was läuft | Verbrauch (Schätzung, `research.md` 1) | Weiter, wenn … |
|---|---|---|---|
| **Spielt** | alles | ~1,6–1,9 W | Ende, Pause, Abheben → **Bereit** |
| **Bereit** | Pi und Dienst laufen; Verstärker aus (SD_MODE), Ring stromlos (MOSFET), Leser lauscht sparsam (LPCD, wenn die Messung passt) | ~1,0–1,3 W | Tobie oder Knopf → **Spielt** (unter 3 s). Ohne Strom am Eingang nach 10 min → **Aus**. Mit Strom am Eingang: bleibt bereit. |
| **Aus** | Pi aus, PiSugar im Ruhezustand; ESP32 im Tiefschlaf, PN5180 spürt Karten (LPCD) | Milliwatt-Bereich (am Muster messen) | Tobie aufgelegt → ESP32 „drückt“ den PiSugar-Einschalter → Pi startet → Tobie spielt (Ziel 10 s). Hauptknopf → Start. Strom an den Eingang → Start → **Bereit**. |

Tagesbudget ohne Sockel (15 Wh nutzbar): Zum Beispiel 4 h Hören (~7 Wh) und 10 Pausen mit je 10 min
Bereitschaft (~2,5 Wh) brauchen knapp 10 Wh. Es bleibt Reserve für das Einschlafen am Abend.

## 4. Was sich gegenüber heute ändert

- **Leerlauf:** 20 min bis „aus“ wird zu **10 min** ohne Strom am Eingang. Mit Strom am Eingang geht die Box **nie** von selbst aus.
  Entscheidung O (Leerlauf zählt auch mit liegendem Tobie) bleibt.
- **Am Sockel:** Der Kurz-Modus mit 120 s aus S2 entfällt: Am Sockel bleibt die Box ja bereit. Andocken weckt die
  ausgeschaltete Box (R8) und bringt sie in den Zustand **Bereit** mit Rückmeldung (Ton und Ring, Leise-Zeiten wie in S5 und S9).
- **Sync und Update am Sockel** werden einfacher: Die Box ist dort immer an. Der Sync läuft im Takt. Ein vorgemerktes
  Update (S6) kann HA jederzeit schicken, solange die Box am Sockel steht. Die Wiederholungsregel für den Start-Sync
  wird überflüssig.
- **Start schneller:** Ein eigenes Arbeitspaket kürzt den Start des Pi (Ziel: Ton nach 10 s). Das kommt auch dem Hauptknopf zugute.
- **Hardware:**
  - Der ESP32 bekommt Strom vom Akku (PiSugar-Pad BAT, Regler auf 3,3 V, Trennung zur USB-Versorgung des Pi).
  - Ein Transistor am PiSugar-Tasterpad 10 erlaubt dem ESP32 das Einschalten. Dafür muss Anti-Mistouch aus.
  - **Der ESP32 steuert den LED-Ring** (E7): Daten- und Taktleitung des Rings wandern vom Pi an den ESP32, ein MOSFET
    (vom ESP32 geschaltet) macht den Ring stromlos. Der Pi sagt dem ESP32 über die serielle Verbindung, was der Ring zeigt.
    Beim Wecken startet der ESP32 sofort das weiße Lauflicht (unter 1 s), lange bevor der Pi bereit ist.
  - Die Belastbarkeit von Pad BAT und die Pegel am Pad 10 werden am Muster geprüft.
- **Pi-seitig:** Leser-Firmware mit Tiefschlaf und LPCD. Ein neues Kommando sagt dem ESP32, wann der Pi ausgeht.
  Ein neues Ereignis meldet „durch Tobie geweckt“. Neue Befehle steuern den Ring. Das alles ändert den Vertrag `reader-v1`.
  Die Ring-Logik (`led.py`) bleibt auf dem Pi, nur die Ausgabe geht an den ESP32.

## 5. Offene Fragen

| # | Frage | Vorschlag der Projektleitung |
|---|---|---|
| E1 | **Powerbank und Auto:** Die Box kann Sockel und Powerbank nicht unterscheiden (S10). Mit Strom am Eingang geht sie nie aus, sie leert also eine Powerbank im Auto (~1,2 W, eine 10-Ah-Powerbank in ~30 h). | **Entschieden (Tobias, 10.11.): hinnehmen.** Wer das nicht will, zieht das Kabel. |
| E2 | **Leser im Zustand Bereit:** Ein MOSFET für den Leser geht nicht, denn er muss Tobies spüren. | **Entschieden (Tobias, 10.11.):** MOSFET nur für den Ring. Der Leser lauscht in Bereit sparsam (LPCD), wenn die Messung am Muster passt (spart ~0,2 W, kostet vielleicht 0,3–0,5 s). |
| E3 | **Akku dauerhaft voll am Sockel:** Er steht Tag und Nacht bei 100 %. | Am Muster prüfen, ob der PiSugar eine Ladegrenze kann; sonst hinnehmen (Akku ist Verschleißteil). |
| E4 | **„Einschalten bei Strom“ ist laut Datenblatt ab Werk an** (`research.md` 4.1), der Plan ging von „aus“ aus. Herunterfahren am Sockel (Hauptknopf lang) könnte sofort neu starten. | Am Sockel ist Herunterfahren selten. Messen; startet sie neu, ist das am Sockel sogar gewollt („immer bereit“). |
| E5 | **Wecken durch Tobie nachts** unter „stumm“: Die Box steht dann meist am Sockel und ist sowieso bereit. Ohne Sockel weckt der Tobie sie, die Leise-Zeiten gelten wie immer. | Keine Sonderregel. |
| E6 | Was zeigt der Ring im Zustand **Bereit**? Stromlos heißt dunkel. | Dunkel. Ein kurzes Aufleuchten nur bei Bedienung, Andocken und Abziehen. |
| E7 | **Sofortige Rückmeldung beim Hochfahren** (Wunsch Tobias, 10.11.). | **Entschieden (Tobias, 10.11.):** Keine Extra-LED und kein Summer. Der ESP32 steuert den LED-Ring und zeigt beim Wecken sofort das weiße Lauflicht. Der Start-Ton kommt über den Lautsprecher, so früh der Pi es kann (früher eigener Systemdienst, Startzeit am Muster messen). |

## 6. Was aus „Start am Lader“ übernommen wird

- **Gilt weiter:** R8 (Andocken weckt), S1 (jede Stromquelle zählt), S4 (liegender Tobie spielt beim Start, CUJ 20),
  S5 (nachts kein Ton, Ring gedimmt), S7 und S8 (Sync auch über Hotspot, beim Andocken prüfen), S9 (beim Spielen nur Ring),
  S10, S11. Antworten Q3 und Q4 aus `resolve_teil1.md` werden mit dem neuen Konzept gegenstandslos.
- **Entfällt:** S2 und S3 (120-s-Kurz-Modus), die Wiederholungsregel für den Start-Sync (Q1), die 30 s Nachlauf
  für S6 und die Schleifenbremse aus dem Entwurf.
- **Wird einfacher:** S6. Steht die Box am Sockel, schickt HA das vorgemerkte Update, sobald sie meldet, dass sie dort steht.

## 7. Messungen am Muster (Auszug, vollständig in `research.md` 9)

1. Startzeit des Pi 3A+ bis zum Ton, vorher und nach dem Kürzen.
2. Verbrauch in **Bereit** (mit und ohne WLAN, Ring stromlos, Leser Dauerabfrage gegen LPCD).
3. Verbrauch in **Aus** (PiSugar im Ruhezustand plus ESP32 im Tiefschlaf mit LPCD).
4. LPCD mit einem Tonie durch den Deckel: Erkennt er ihn sicher? Weckt er die Box ohne Grund?
5. PiSugar: Pegel und Zeiten am Pad 10, Belastbarkeit von Pad BAT, „Einschalten bei Strom“ (Flanke oder Pegel), Ladegrenze.
