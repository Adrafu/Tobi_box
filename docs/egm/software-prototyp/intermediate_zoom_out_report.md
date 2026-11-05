# Goldfisch-Review Stufe 8 — Zoom-out (Zwischenstand)

**Ziel:** `design_draft.md` (ganz) · **Maßstab:** EGM zoom-out-standard ·
**Prüfer:** frischer Agent (Sonnet) · **Datum:** 2026-11-05

Urteil: keine Blocker, 8 Major, 4 Nits. Stufe-5-Lösungen umgesetzt; durch
Stufe 6/7 sind Parallel-Mechanismen und Doppelungen dazugekommen.

## Vorschlag der Projektleitung

| # | Lösung |
|---|---|
| 1 | **Ja:** Stufe 3 teilen. 3a = HA-Integration + Seite + Box↔HA + Sync + Tailscale (CUJ 7a/7b, 9, 12). 3b = Update mit Signatur und Rückfall + Lautheit + Handbuch (CUJ 10). Getrennte Abnahmen; Go/No-Go vor 3a. |
| 2 | **Ja:** ReplayGain nur dämpfend (Vorverstärkung 0, keine positive Anhebung); Test prüft die Konfiguration; echte Prüfung = Messung am Verstärker, offen so benannt. Klemmen an zwei Stellen: Kern berechnet, MPD/ALSA als harte Außen-Sicherung. |
| 3 | **Ja:** Kurzablauf im Selbsttest streichen; Schemas: Rückspielen der Sicherung ist die Regel; 5-min-Timer ersetzt durch „Selbsttest nicht in 5 min bestanden → Dienst beendet sich → Startzähler greift“. Signatur bleibt, mit Standardwerkzeug `minisign`; Zweck benannt (Schutz gegen manipuliertes NAS/Netz). |
| 4 | **Ja:** Lautheitsmessung nur per Zeitplan im Container (alle 15 min), kein HA-Auslöser. Eine vor dem Messen geholte Datei wird einmal nachübertragen; das ist hingenommen. Dritter Schreiber in die Risiko-Tabelle. |
| 5 | **Ja:** Ein Thema `tobibox/config` (dauerhaft) mit Zuordnungen **und** Leise-Zeiten (und Gute-Nacht-Einstellungen), eine Revision, eine Listen-ID. „Erzwingen“ heißt „Liste neu ausrollen“ (neue Listen-ID). Rückweg: HA-Sicherung + automatischer NAS-Export; Import aus Box-Kopie entfällt. |
| 6 | **Ja:** Konfliktliste und Tabellen zu **einer** Konflikt-Tabelle zusammenführen (= Abnahmetests); Vorrang nur noch als ein Satz für unvorhergesehene Fälle; doppelte Zeile zusammenlegen; Zeile „Figurwechsel während Leser-Unterbrechung“ ergänzen. |
| 7 | **Ja:** Zeit unsicher → kleinste „leiser“-Grenze aller Fenster, nie stumm. AP 4.5 mit Sonnet. Verteilung über `tobibox/config`. |
| 8 | **Teilweise:** ein gemeinsamer Simulations-Treiber für alle Eingänge (Tastatur/Terminal); LED-Ring als Zustandsanzeige im Terminal und im Log, keine HA-Anzeige. `power` + Simulation komplett in AP 3.3. Die APs 4.1–4.4 bleiben getrennt (parallel baubar), nutzen aber den einen Treiber. |
| 9 | **Ja:** Überraschungs-Serie nur über `typ=ueberraschung` (keine feste ID). Reihenfolge: Liste in `serie.json`, sonst Dateiname; Dateien außerhalb der Liste spielt die Box erst, wenn die Integration sie eingetragen hat. |
| 10 | **Teilweise:** Papierkorb ohne Automatik, mit Knopf „Papierkorb leeren“ auf der Seite; Kopierschutz = „ffprobe kann die Datei nicht öffnen → Warnung“; Speicheranzeige bleibt (Box meldet freien Platz mit dem Status). |
| 11 | **Ja:** Ein Protokollweg je Gerät: am Pi journald dauerhaft mit JSON, am Mac rotierende Datei (Konfiguration). `ack`-Thema streichen: MQTT QoS 1 + dauerhafte Sitzung, Verarbeitung idempotent; `unknown.json` bleibt, bis der Broker bestätigt. |
| 12 | **Ja:** CUJ 14 umformulieren (Serien-Figur weg, Karte auf); Dauer von Timer und Ausblenden als Einstellung in HA (Vorschlag 30 min, Ausblenden 60 s); Zuordnen von Aktionskarten auf der HA-Seite. |

---

## Rohtext des Prüfers

Zoom-Out-Review Stufe 8 (Zwischenstand) zu `design_draft.md`, 1522 Zeilen.

Gelesen: ganzer Entwurf, `zoom_out_report.md`, `critic_report.md` (Befunde und Vorschläge der Projektleitung), `comprehension_report.md`. Code-Suche war nicht nötig: Es gibt noch keinen Box-Code, nur `firmware/tonie_test/` als Referenz.

**Gesamturteil.** Die Stage-5-Auflösungen sind fast alle sauber umgesetzt:
- Stufe 0 hat nur noch zwei Dateien.
- pytest-Tabellen ersetzen das Szenario-Format.
- Python `logging` ersetzt den Ringpuffer.
- `admin_cards.json` ist weg.
- Sync-Regel und `--delete`-Schutz stehen.

Zwei Abweichungen sind bewusst und im Dokument begründet:
- Die HA-Seite bleibt in Stufe 3 (D4, steht unter Alternativen). Das ist eine Autorenentscheidung, und ich stelle sie nicht in Frage.
- Die Gute-Nacht-Karte ist wieder im Umfang (Stufe 4, Ziel 9).

Die Stage-6/7-Auflösungen haben dem Design aber mehrere Parallel-Mechanismen und Redundanzen hinzugefügt. Ich sehe keinen Blocker, aber 8 Majors. Reihenfolge nach Schwere:

---

**1. Major — Stufe 3 ist eine Mega-Stufe (Zeilen 1371–1451, 1359–1369)**
- Stufe 3 enthält jetzt 8 APs: HA-Integration, HA-Seite, Box↔HA, Sync, Update mit Signatur, Tailscale, Handbuch, Lautheit. Dazu kommen 7 Abnahmetests und ein Go/No-Go mit vier Voraussetzungen.
- Stage-5-Befund 1 ("größtes Bauteil") ist damit nur teilweise gelöst. Die Seite blieb in Stufe 3, dazu kamen Update und Lautheit.
- Respektiert: D4 ("Seite in Stufe 3").
- Challenge: Update (D-Wunsch "HA-Knopf bleibt") und Lautheit sind von Zuordnung/Sync unabhängig und hängen nicht an der Seite.
- Empfehlung: Stufe 3 teilen.
  - **3a:** HA-Integration + Seite + `ha.py` + Sync + Tailscale. Das erfüllt CUJ 7a/7b, 9, 12.
  - **3b:** Update/Signatur/Rückfall + Lautheit + Handbuch. Das erfüllt CUJ 10.
  - Abnahme und Go/No-Go jeweils getrennt. So kann 3a produktiv laufen, während das riskante Update-System noch reift.

**2. Major — "Keine Lautstärke liegt über der Grenze, auch nicht durch ReplayGain" ist so nicht prüfbar (Zeilen 676–695, AP 3.8 Zeile 1442, Ziel 10)**
- MPD wendet ReplayGain intern auf das PCM-Signal an, nicht über den Mixer-Wert. `replaygain_limit` verhindert nur Clipping.
- Die Dienst-Grenze (`volume`/`player`) sieht ReplayGain also gar nicht. Der Test "Lautstärke überschreitet die wirksame Grenze nie" (`test_replaygain_limit.py`) würde den MPD-Mixerwert prüfen und wäre damit leer. Gemessen werden kann es nur am Verstärker (Stufe 4).
- Das ist die Kinderohren-Garantie (Ziel 10) und sollte nicht auf einer Scheinprüfung stehen.
- Empfehlung: ReplayGain nur **dämpfend** betreiben, nicht anhebend.
  - Konservativer Ziel-Pegel in `rsgain` und MPD-Einstellung ohne positive Anhebung (z. B. `replaygain_missing_preamp`, Vorverstärkung 0).
  - Der Test prüft dann die Konfiguration: Max-Gain ≤ 0 dB.
  - Die echte Prüfung ist die Verstärker-Messung, im Text offen als solche benannt.
- Zusätzlich dreifach geklemmt: `volume` im Kern, `player` und MPD/ALSA. Zwei reichen (Kern berechnet, MPD/ALSA als harte Außen-Sicherung); `player` muss nicht ein drittes Mal klemmen.

**3. Major — Update-Rückfall: weiterhin vier ineinandergreifende Auslöser plus Signatur-Infrastruktur (Zeilen 992–1029, AP 3.5)**
- Stage-5 #3 hat "systemd-Mittel" verlangt. Das Ergebnis enthält:
  - Startzähler nur im Zustand `testing`,
  - `OnFailure=`,
  - ein systemd-Timer für "testing älter als 5 min",
  - eine Entscheidungsfunktion mit Test,
  - Sicherung/Rückspielen der Zustandsdateien,
  - atomare Verweis-Umstellung,
  - `manifest.json` mit 4 Versionsfeldern,
  - Signatur samt zwei Skripten (`build_release.sh`, `sign_release.sh`) und Schlüsselverwaltung,
  - zusätzlich den Selbsttest mit "fest eingebautem Kurzablauf gegen den Kern".
- Der Kurzablauf gegen den Kern ist auf dem Pi derselbe Code, den CI schon prüft. Er bringt nur Kosten (Stage-5 #3 wollte "Dienst läuft, HELLO, MPD, Testton").
- Doppelt abgesichert sind auch die Schemas: "nur abwärtskompatibel" **und** Sicherung/Rückspielen.
- Empfehlung:
  - Kurzablauf streichen.
  - Eine der beiden Schema-Sicherungen streichen. Das Rückspielen der Sicherung deckt es ab; die Kompatibilitätsregel ist dann nur ein Hinweis.
  - Den 5-min-Timer durch "Selbsttest nicht innerhalb 5 min bestanden → Dienst beendet sich → Startzähler greift" ersetzen. Das ist ein Mechanismus weniger.
  - Signatur: ein Standardwerkzeug festlegen (`minisign` oder `ssh-keygen -Y verify`), kein eigener Code.
  - Zur Signatur: Das Risiko "HA hat Schreibrecht" (Zeile 284) ist durch "`releases/` für HA nur lesbar" schon entschärft. Signatur schützt dann nur gegen ein kompromittiertes NAS oder Tailscale. Das ist vertretbar, aber das Dokument sollte das so benennen. Ob sich das für zwei Boxen daheim lohnt, entscheidet Tobias.

**4. Major — D6: HA löst einen Container auf dem NAS aus (Zeilen 229–238, 903, 1434–1441)**
- Das ist ein neuer, nicht beschriebener Pfad: HA (Add-on) → QNAP-Container-Start. Mechanismus fehlt (SSH, Webhook, Container-Station-API?).
- Er widerspricht der Sicherheitslinie "HA nur `medien/` und `export/` schreiben". Ein kompromittiertes HA könnte so Code auf dem NAS auslösen.
- Es entsteht ein **dritter Schreiber** auf den Medien (HA, PC, `rsgain`). Er fehlt in der Risikotabelle (Zeile 280 nennt nur zwei).
- Zusätzlich ändern ReplayGain-Tags die Dateien, damit schickt rsync sie erneut an beide Boxen. Das trifft die Regel "spielende Datei wird nie ersetzt".
- Empfehlung:
  - Nur **Zeitplan** im Container (nachts per cron im Container), kein HA-Auslöser. Das streicht den Auslöser in `media.py` und die Zeile in AP 3.8.
  - Lautheits-Tags schreiben, bevor die Box sie holt (zuerst Lautheit, dann Sync). Wenn Tags erst nach dem ersten Sync entstehen, wird jede neue Datei zweimal übertragen. Das ist eine Reihenfolge-Frage, kein Code.

**5. Major — Verteilung und Wiederherstellung der Zuordnungen: fünf Teile für einen Fall (Zeilen 884–887, 950–962, AP 3.1)**
- Es gibt Revision, Listen-ID, die Aktion "erzwingen", automatischen Export aufs NAS **und** Import aus einer Box-Kopie, dazu die Meldung "abgelehnte Liste". Alle dienen demselben Fall (HA wird wiederhergestellt).
- "Erzwingen" ist redundant: Es ist dasselbe wie "HA erzeugt eine neue Listen-ID". Die Listen-ID-Regel deckt es bereits ab.
- Zusätzlich wird für Leise-Zeiten (AP 4.5, Zeile 1498) derselbe Mechanismus noch einmal ("MQTT, dauerhaft, mit Revision und Listen-ID wie die Zuordnungen") für eine zweite Liste gebaut.
- Empfehlung:
  - "Erzwingen" streichen. Die Aktion heißt "Liste neu ausrollen" und erzeugt eine neue Listen-ID.
  - **Ein** Konfigurations-Thema `tobibox/config` (retained) mit Zuordnungen **und** Leise-Zeiten, eine Revision, eine Listen-ID. So entfällt der zweite Verteilweg.
  - Nur einen Rückweg aufbewahren. NAS-Export ODER Import aus Box-Kopie, nicht beides. HA-Sicherung plus NAS-Export reichen; die Box-Kopie ist ohnehin die dritte Sicherung.

**6. Major — Kern-Zustände: Vorrang-Liste und Konfliktliste doppeln die Tabellen (Zeilen 802–827, 708–800)**
- Das Dokument hat vier Teilautomaten mit Tabellen, zusätzlich die Vorrang-Liste (5 Stufen) **und** eine Konfliktliste mit 6 Punkten.
- Die Konfliktliste wiederholt Zeilen aus den Tabellen:
  - "Gute Nacht + andere Figur" steht in der Gute-Nacht-Tabelle, Zeile 779.
  - "Abheben beim Ausblenden" steht in der Gute-Nacht-Tabelle, Zeile 782.
  - "Stumm beginnt" steht in der Sitzungs-Tabelle, Zeile 736.
- Die Vorrang-Liste (5 Stufen) wird sonst nirgends gebraucht. Jeder Konflikt ist einzeln aufgelöst, und ein Agent implementiert die Konflikte, nicht die abstrakte Rangfolge.
- In der Tabelle "Strom / Leerlauf" gibt es zwei fast gleiche Zeilen (Zeilen 792/793).
- Es fehlt eine Zeile für `unbekannt` + `HELLO` + `PLACED` mit **anderer** Kennung (Figurwechsel während der Leser-Unterbrechung).
- Empfehlung:
  - Konfliktliste und Vorrang-Liste streichen. Stattdessen **eine** Tabelle "Konflikte → erwartetes Ergebnis", die zugleich die Abnahmetests von Stufe 4 (Zeile 1510) ist.
  - Zeilen 792/793 zusammenlegen.
  - Fehlende Zeile ergänzen.

**7. Major — Leise-Zeiten (CUJ 15, AP 4.5): Spezifikation und Modellwahl passen nicht (Zeilen 431–445, 697–706, 1494–1500)**
- "Strengste Leise-Wirkung **des Tages**" bei nicht vertrauenswürdiger Zeit ist nicht definierbar: Ohne vertrauenswürdige Zeit kennt die Box den Tag und den Wochentag nicht (Fenster hängen an Wochentagen).
- Ein beliebig langer Fensterbestand (Wochentage, Wirkung je Fenster) ist ein Mini-Kalender.
- Wenn das Verhalten auf "stumm" fällt, hat die Box nach leerem Akku am Wochenende morgens Stille. Das wirkt wie ein Defekt.
- AP 4.5 ist mit Haiku besetzt. Die Logik (Zeitfenster, Vorrang, ausblenden, Zeitquelle) ist Teil des Kerns mit Hardware-Bezug. Die CLAUDE.md-Regel nennt dafür Sonnet.
- Respektiert: Die frei einstellbaren Leise-Zeiten in HA sind Autorenanforderung.
- Empfehlung:
  - Fallback bei unsicherer Zeit: kleinste Fenster-Grenze (leiser), nie stumm. Eine Zeile, kein "des Tages".
  - AP 4.5 auf Sonnet.
  - Leise-Zeiten über das Thema aus Befund 5 verteilen, nicht über einen eigenen Mechanismus.

**8. Major — Stufe 4: Simulationsaufwand wuchert (Zeilen 636, 1453–1514, 987)**
- Vier Hardware-Module haben je Schnittstelle plus Sim-Treiber plus Test: `led`/`led_sim`, `controls`/`controls_sim`, `power`/`power_sim`, `headphones`/`headphones_sim`. Dazu kommen `tobibox sim …` als CLI und ein "virtueller Ring (Terminal- oder HA-Anzeige)".
- Die HA-Anzeige des Rings ist ein eigener Mini-Baustein, der zu nichts anderem gehört.
- Zusätzlich ist `power` auf zwei Stufen verteilt. AP 3.3 liefert `power.py` ("Strom-Schnittstelle (Simulation)"), AP 4.3 ändert es und liefert erst dann `power_sim.py`. Wer simuliert in Stufe 3 die Akku-Regel für den Sync (Zeile 987: "ab Stufe 3 … `tobibox sim power`")?
- Respektiert: Ziel 9 (keine Funktion wartet auf Hardware, Simulation am Mac).
- Empfehlung:
  - Ein gemeinsames Hardware-Eingangsmodul mit **einem** Sim-Treiber (Tastatur/Terminal), der alle vier Eingänge liefert. Kein HA-Ring.
  - LED nur als Zustandslog/Test, nicht als grafische Anzeige.
  - `power` + `power_sim` komplett in Stufe 3 (AP 3.3), Stufe 4 liefert nur noch `idle.py` und die PiSugar-Beschreibung.
  - AP 4.1–4.4 zu einem AP zusammenfassen (ein Agent, ein Review).

**9. Major (knapp) — Drei Mechanismen für die Serien-Identität (Zeilen 38–39, 207–213, 848–852, 872, 894–897)**
- (a) `serie.json` mit zufälliger, unveränderlicher `id`.
- (b) Fallback "Ordnername als ID" für Ordner ohne `serie.json`.
- (c) Eine **feste** ID `ueberraschung`, dazu zusätzlich das Feld `typ` in `serie.json`.
- Das ist widersprüchlich: Die Überraschungs-Serie hat laut Begriffen eine feste ID, laut Zeile 894 aber hat jede `serie.json` eine zufällige ID. Wenn die Regel "jüngere Kopie bekommt neue ID" greift, könnte sie die feste ID zerstören.
- Auch die Reihenfolge hat drei Schichten: Liste in `serie.json`, Dateiname-Fallback, "nicht gelistete Dateien hinten dran".
- Respektiert: D2 (`serie.json` bleibt).
- Empfehlung:
  - Überraschungs-Serie nur über `typ=ueberraschung` identifizieren; keine feste ID. Die Konfiguration der Box verweist darauf.
  - Wenn `typ` dafür da ist, Begriff und Zeile 872 anpassen.
  - Reihenfolge: Liste in `serie.json`, sonst Dateiname. Die Mischregel ("hinten dran") kann entfallen, weil die Integration neue Dateien ohnehin hinten an die Liste hängt (Zeile 900).

**10. Nit — Medienverwaltung: Zusatzfunktionen vor dem ersten Nutzen (Zeilen 898–907, 224–228, AP 3.1/3.2)**
- Papierkorb mit **30 Tagen** braucht einen Aufräum-Job (nicht beschrieben).
- "Kopierschutz prüfen" (D5) hat keinen Mechanismus (ffprobe? Endung `.m4p`?).
- "Speicher je Box-Kapazität" braucht, dass die Boxen ihre Kapazität melden.
- Die 10-min-Abfrage der Freigabe läuft zusätzlich zum Öffnen der Seite.
- Respektiert: D4/D5. Challenge: alle drei sind nach Bedarf nachrüstbar.
- Empfehlung:
  - Papierkorb ja, aber ohne Automatik (Tobias leert ihn von Hand).
  - DRM-Prüfung als "Datei lässt sich mit ffprobe nicht öffnen → Warnung".
  - Speicheranzeige ist Sache von Stufe 3b.

**11. Nit — Doppelte Ablagen und Absicherungen**
- **Log:** `RotatingFileHandler` auf dauerhaftem Speicher **und** journald dauerhaft auf dem Pi (Zeilen 1033–1040, AP P.1 `journald-tobibox.conf`). Das sind zwei dauerhafte Protokolle mit zwei Obergrenzen, die im Pi-Probelauf geprüft werden.
  - Empfehlung: Einen Weg wählen. Wenn journald dauerhaft ist, reicht es mit JSON-Formatter; die Datei entfällt (und der SD-Verschleiß sinkt).
- **`ack`-Thema:** `tobibox/<box>/ack` (Zeile 941) duplizieren, was MQTT QoS 1 plus persistente Sitzung leistet. Der Broker läuft in HA; ein Verlust zwischen Broker und Integration lässt sich mit einer idempotenten Verarbeitung abfangen. Der Preis des Entwurfs ist ein Thema mehr, Zustände auf beiden Seiten und eine Testfläche. Empfehlung: QoS 1 plus idempotent, `ack` streichen. Das gilt nur, wenn `unknown.json` bis zur Broker-Bestätigung bleibt (Offline-Fall bleibt abgedeckt).

**12. Nit — Kleine Lücken im Gute-Nacht-/Aktions-Pfad (Zeilen 421–429, 774–782, 853–855, 1387–1389)**
- CUJ 14 sagt "Given: Eine Serie spielt … legt die Gute-Nacht-Karte auf". Auf dem Leser liegt aber immer nur **eine** Figur. Die Serien-Figur muss erst weg (Pause), dann kommt die Karte. Das Design der Tabelle stimmt damit (Karte zuerst, danach die Serie, Zeile 779), das CUJ ist aber falsch formuliert.
- Die **Dauer** des Gute-Nacht-Timers und des Ausblendens ist nirgends festgelegt (Konfiguration? je Karte?).
- AP 3.2 (HA-Seite) listet keine Bedienung, um eine Karte einer **Aktion** zuzuordnen (Status, Gute Nacht), obwohl Zeile 853–855 sagt "in HA wie jede Figur zugeordnet".
- Empfehlung: CUJ 14 umformulieren, Timer-Dauer als Konfigurationswert festlegen, Aktions-Zuordnung in die Seite aufnehmen. Alles kleine Änderungen.

---

**Was ich bewusst nicht beanstande:**
- Die Dateitabellen in den APs (Stage-5-Auflösung 5: EGM verlangt sie dort).
- Ziel 9 und die vier Autorenanforderungen: Stufe 4 mit Simulation, HA-Seite in Stufe 3, Lautheit auf dem NAS, Leise-Zeiten in HA.
- Den Begriffsblock (Stage-6-Auflösung).

**Gelesene Dateien:**
- `/home/user/Tobi_box/docs/egm/software-prototyp/design_draft.md`
- `/home/user/Tobi_box/docs/egm/software-prototyp/zoom_out_report.md`
- `/home/user/Tobi_box/docs/egm/software-prototyp/critic_report.md`
- `/home/user/Tobi_box/docs/egm/software-prototyp/comprehension_report.md`
