# Ladestation: Folgen für die Box-Software

* **Datum:** 10.11.2026
* **Grundlage:** `resolve.md` (R8, R9, R10), `design_draft.md` (Rev. 4),
  `docs/designs/box-software.md`, `docs/protocol/*`, `docs/data-model.md`,
  `docs/plan/stueckliste-und-psp.md`, `docs/betrieb/pisugar-wecker.md`,
  Code `box/src/tobibox/` (Stand Repo)
* **Stand:** Analyse, nichts umgesetzt. Kein Code, kein Vertrag, kein Design
  geändert. Verträge sind nur benannt (Punkt 7). Tobias entscheidet nach dem EGM.

Kurz vorweg: Vieles ist im Code schon da. `idle.py` startet am Lader schon
`SyncStarten("start_lader")`, `led.py` zeigt bei `LaderGeaendert` schon fünf
Sekunden den Ladestand (blau am Lader). Es fehlen: ein kurzer Abschalt-Zähler,
ein eigener Ton, Leise-Zeiten für Ton und Ring, ein schnelleres Erkennen des
Andockens und eine Regel gegen ungewollten Sync unterwegs.

---

## 1. Startgrund: Woher weiß die Box, dass der Lader sie geweckt hat?

### Was belegt ist

| Aussage | Quelle | Status |
|---|---|---|
| pisugar-server kennt `get battery_power_plugged` („charging usb plugged, new model only“) und `get battery_charging` (für neue Modelle nicht empfohlen). | README `PiSugar/pisugar-power-manager-rs` (gelesen 10.11.) | belegt. `power.py` nutzt schon `battery_power_plugged` |
| Ein Schalter „Auto-Power-On“ existiert. README: „`auto_power_on` mode would prevent PiSugar falling into sleep“, Datei `/etc/pisugar-server/config.json`, seit v1.4.8. Es steht **kein** `get`/`set`-Befehl in der Befehlsliste. | dieselbe README | belegt, aber **Bedeutung unklar**: „verhindert Einschlafen“ ist nicht dasselbe wie „startet bei Strom“ |
| Ein Pwnagotchi-Gist benutzt `get auto_power_on` und `set_auto_power_on true/false` über den Socket. | gist.github.com/darkr4y/89704967bca22d24d21032ebe70e7310 (nur Suchtreffer, nicht selbst geprüft) | Hinweis, **nicht belegt** für PiSugar 3 Plus |
| Die PiSugar-Wiki führt „Automatic power on when external power is restored“ als unterstützt für PiSugar 1, S, 2 und **3**. | github.com/PiSugar/PiSugar/wiki/PiSugar-3-Series (Wiki ist nach docs.pisugar.com umgezogen, nicht mehr gepflegt) | belegt als Funktion, aber ohne Ablauf |
| Eine Fremdseite (Gardenbot) zeigt in der PiSugar-Web-Oberfläche „Schedule Wake up Config = On Power Restore“. Der Pi startet, wenn man das Netzkabel abzieht und wieder einsteckt. | digitalhabitat.github.io/gardenbot/.../pisugar.html | Hinweis, ein Fremdbericht |
| Es gibt Wecken per RTC-Alarm (`rtc_alarm_set`, `rtc_alarm_disable`, `get rtc_alarm_enabled`, `get rtc_alarm_time`). | README | belegt |

### Was nicht belegt ist

* **Ein Befehl oder Ereignis „Startgrund“** (Lader, Knopf, Wecker) gibt es in
  der README nicht. Dort steht ausdrücklich nichts darüber, wie der Pi nach dem
  Start erfährt, warum er läuft.
* **Ereignisse** des pisugar-server sind nur Tasten (`button_shell` für einfach,
  doppelt, lang) und das automatische Herunterfahren bei niedrigem Akku
  (`safe_shutdown_level`). Ein Ereignis „Netzteil gesteckt“ gibt es nicht.
  Man muss `battery_power_plugged` abfragen.
* **docs.pisugar.com** wurde nicht ausgewertet (WebFetch der Wiki-Seite verwies
  dorthin). Das ist offen, wenn Tobias den Punkt vor dem Muster klären will.
* Ob „Power Restore“ **nur bei einer Flanke** (Strom kommt neu) startet oder auch,
  wenn die Box mit Strom am Eingang heruntergefahren wurde (Boot-Schleife am
  Sockel), ist nicht belegt. Das ist das größte Risiko von R8 und gehört in
  T5 (siehe Punkt 9).
* Ob ein Knopfdruck am Sockel (Box aus, Strom schon da) denselben Start
  auslöst wie das Andocken: ja, er startet, aber die Software sieht keinen
  Unterschied (siehe unten).

### Folgerung

Die Software kann den Startgrund **nicht sicher** erkennen. Was sie sicher
weiß: `battery_power_plugged == true` beim Start, und ob der Start ein echtes
Einschalten war (nicht nur ein Neustart des Dienstes): `bootid.py` und
`lauf.json` (Entscheidung G) leisten das schon.

Ein Merker „war beim Ausschalten am Lader“ hilft nur zum Teil:

| Merker beim letzten Ausschalten | jetzt Strom am Eingang | Schluss |
|---|---|---|
| nicht am Lader (oder fehlt, Akku war leer) | ja | sicher Andocken (ein Knopfdruck am Sockel geht nur, wenn die Box schon dort stand und startete) |
| am Lader | ja | **unklar**: Knopf am Sockel, oder Box im Aus abgehoben und wieder angedockt (der Pi sieht das Abheben nicht) |

Der zweite Fall ist der Alltag (Box aus am Sockel, tagsüber abgehoben, abends
wieder aufgesetzt). Deshalb taugt der Merker nicht als Grundlage.

**Vorschlag:** Die Software braucht den Grund gar nicht, wenn der Ablauf
gutmütig ist. Bedingung „Start am Lader“ = echtes Einschalten (neue `boot_id`)
**und** Strom am Eingang. Der Kurz-Zähler (Punkt 2) wird durch jede Handlung
beendet, und er ist so lang, dass ein Kind, das den Knopf gedrückt hat, ihn
nicht verpasst. Ein Dienst-Neustart (Update, Absturz) löst nichts davon aus.

**Am Muster nachzusehen** (kostet nichts): `help xx` im Socket, die I²C-Register
des PiSugar 3 (ob ein Bit „Einschaltgrund“ existiert), Inhalt von
`/etc/pisugar-server/config.json` mit und ohne den Schalter.

---

## 2. Neuer Ablauf „Start am Lader“ (Teilautomat Strom / Leerlauf)

Betrifft `box-software.md`, Tabelle „Strom / Leerlauf“, CUJ 16, und
`core-interface.md`, `idle.py`-Zeile. Im Code: `idle.py` (`_start_pruefung`,
`LEERLAUF_S`, `belegt`, `_auswerten`).

### 2.1 Schritte

1. **Start:** Dienst startet, `Bereit` kommt. Echtes Einschalten (neue
   `boot_id`) und `am_lader == True`. Sonst gilt alles wie bisher.
2. **Rückmeldung** (Punkt 4 für nachts): Ton `lader` (neu) und Ring zeigt „lädt“
   mit Ladestand, etwa 5 s (`AKKU_ANZEIGE_S` gibt es schon).
3. **Sync prüfen:** erst warten, bis `NetzKlasse` bekannt ist (höchstens
   `LADER_NETZ_WARTE_S`, Vorschlag 45 s), dann `SyncStarten("start_lader")`. Das
   füllt die Lücke aus `docs/betrieb/pisugar-wecker.md`, Abschnitt 6: Heute
   würde `sync` bei noch nicht verbundenem WLAN `netz_weg` melden und die Box
   ohne Sync ausgehen.
4. **Kurz-Zähler:** läuft ab dem Ende der Rückmeldung. Dauer
   `LADER_KURZ_S`, **Vorschlag 120 s** (statt `LEERLAUF_S` = 1200 s). Warum nicht
   kürzer: Der Zähler muss den Knopf-Start am Sockel mit abdecken (Punkt 1),
   und am Lader kostet Laufzeit keinen Akku. Ein Sync oder Update hält die
   Abschaltung auf wie bisher; nach Ende wird sofort geprüft.
5. **Herunterfahren:** wie bisher `HerunterfahrenAngefordert`, Zeiger gespeichert,
   Grund `lader_kurz` (für das Protokoll).

### 2.2 Zustände und Übergänge (Vorschlag)

Kleinste Änderung im Code: kein neuer Modus, sondern ein Merker `kurz` im
Zustand und eine Frist-Funktion statt der festen Konstante. Zur Verständlichkeit
hier als Tabelle mit dem Merker als Zustand `lader_start`:

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| beim Start | `Bereit`, neue `boot_id`, am Lader, kein Tobie liegt/spielt | Rückmeldung (`LaderMelden`, `TonSpielen("lader")`), auf Netz warten, dann `SyncStarten("start_lader")` | `lader_start` |
| `lader_start` | Rückmeldung zu Ende, Sync beantwortet oder nicht fällig | Zähler `LADER_KURZ_S` starten | `lader_start` (Zähler läuft) |
| `lader_start` | Zähler um, Sync/Update/Lernmodus läuft | warten, nach Ende sofort prüfen | `lader_start` |
| `lader_start` | Zähler um, nichts läuft | Zeiger speichern, Herunterfahren (`lader_kurz`) | `herunterfahren` |
| `lader_start` | Tobie aufgelegt (Sitzung belegt) | Kurz-Zähler verwerfen | `aktiv` (danach normale 20 min nach Leerlauf) |
| `lader_start` | Hauptknopf kurz | Kurz-Zähler verwerfen, „wach halten“ | `leerlauf` mit 20 min ab jetzt |
| `lader_start` | Hauptknopf lang | Zeiger speichern, Herunterfahren | `herunterfahren` |
| `lader_start` | `LaderGeaendert(false)` (jemand hebt die Box ab) | Kurz-Zähler verwerfen | `leerlauf` mit 20 min ab jetzt |
| `lader_start` | HA-Befehl `HaUpdateAnstossen`, Lernmodus | Kurz-Zähler verwerfen (Lernmodus und Update halten ohnehin) | `aktiv`/`leerlauf` |
| `lader_start` | `AkkuTiefstand` | ignoriert (am Lader, wie heute) | gleich |

### 2.3 Abbruch durch das Kind

* **Tobie auflegen:** `SitzungGeaendert` mit `figur_liegt` oder `spielt` macht
  die Box „belegt“. Das erkennt `idle.py` schon. Neu ist nur, dass dann `kurz`
  gelöscht wird.
* **Knopf:** `Hauptknopf` kurz ist ein Eingang von `idle.py`, wird aber heute
  ignoriert. Neu: im Kurz-Modus beendet er ihn. `Weiter`, `Zurueck` und
  `LautstaerkeDrehen` sind **keine** Eingänge von `idle.py` (Zeile in
  `core-interface.md`, Tabelle der Teilautomaten). Sie dazunehmen ist ein
  Vertragseingriff; ohne Tobie tun sie ohnehin nichts. **Empfehlung:** nur
  `Hauptknopf` kurz, Tobie und `LaderGeaendert(false)` zählen.
* Der Satz in `idle.py`, Bedienung setze den Zähler **nicht** zurück, bleibt für
  den normalen Leerlauf. Er gilt nur im Kurz-Modus nicht.

### 2.4 Zusammenspiel mit CUJ 20 (Tobie liegt beim Start)

Heute spielt ein beim Einschalten liegender Tobie sofort (CUJ 20). Beim Andocken
einer ausgeschalteten Box mit liegendem Tobie würde sie also **anfangen zu
spielen**, nicht nur „lädt“ zu zeigen. Das widerspricht „ohne Wiedergabe“ aus
R8. Nachts verhindert das Fenster „stumm“ die Wiedergabe, ein Fenster „leiser“
nicht. Ohne sicheren Startgrund (Punkt 1) lässt sich Andocken und Knopf nicht
trennen. Siehe Entscheidung 4.

### 2.5 Was am Ring und Ton in der Zeit vor `Bereit` ist

Der Pi 3A+ braucht 20 bis 30 s (Schätzung im Resolve). In dieser Zeit zeigt die
Box nichts. Das ist für ein Kind eine lange Pause nach dem Aufsetzen. Mögliche
Abhilfe ohne Vertrag: ein kleiner Frühstart-Dienst, der den Ring in den ersten
Sekunden des Bootens blau schaltet. Erst messen (T5), dann entscheiden.

---

## 3. Andocken bei laufender Box

Auslöser: `LaderGeaendert(true)` bei laufender Box (nicht beim Start).

### 3.1 Wie schnell wird das erkannt?

`power.py` fragt alle `intervall_s = 10` s (Konfiguration `[strom]`). Das ist zu
langsam für „Rückmeldung sofort“ (bis 10 s Verzögerung). pisugar-server hat
nach der README **kein** Ereignis für „Netzteil gesteckt“ (Punkt 1). Vorschlag:
eigene schnelle Abfrage nur für `battery_power_plugged`, alle 1 bis 2 s;
Akkustand bleibt bei 10 s. Eine kleine TCP-Anfrage an localhost kostet fast
nichts (am Muster messen).

### 3.2 Entprellen

Gemeint ist Wackeln, also `true`, `false`, `true` binnen weniger Sekunden. Zwei
verschiedene Dinge trennen:

* `LaderGeaendert` selbst bleibt **unverzögert** und richtig (die Regeln für
  Hotspot und Update brauchen den echten Wert). Mit der 1-bis-2-s-Abfrage fängt
  `power.py` die schnellsten Aussetzer von selbst heraus.
* Die **Rückmeldung** (Ton, Ring) bekommt eine Sperre `LADER_MELDUNG_SPERRE_S`,
  **Vorschlag 10 s**: Nach einer Rückmeldung gibt es 10 s lang keine weitere,
  weder für „gesteckt“ noch für „abgezogen“. Die erste kommt sofort, nicht erst
  nach 10 s Wartezeit.

### 3.3 Welche Rückmeldung bei laufender Box?

| Lage | Ton | Ring |
|---|---|---|
| Leerlauf, `leer`, `pausiert`, `gehalten`, `beendet` | `lader`, kurz | „lädt“ mit Stand, 5 s |
| Hörspiel **spielt** | **kein Ton** (das Hörspiel nicht stören, `ton_pause` pausiert es sonst) | Ring 3 s „lädt“, dann zurück zu „läuft“ |
| Lernmodus | kein Ton | Ring kurz |
| Leise-Zeit | siehe Punkt 4 | gedimmt |

Dazu eine Kleinigkeit: Wird die laufende Box angedockt, ist ein Sync-Check
sinnvoll (wie beim Start). Im Code heute nicht: `_start_pruefung` läuft nur
einmal nach `Bereit`. Siehe Entscheidung 8.

### 3.4 Abziehen

* Ring: Akkustand 5 s in Ampelfarben (`led.py` macht das schon:
  `LaderGeaendert` löst `akku_zeigen` aus, ohne Lader nicht blau). Kein Ton.
* `idle.py`: Im Kurz-Modus beendet Abziehen den Modus (Punkt 2). Sonst bleibt
  der 20-min-Zähler, wie er ist.
* Andere Folgen am Strom: `AkkuTiefstand` ist wieder scharf (`power.py`,
  `_tiefstand_pruefen`, wenn `am_lader` `False` ist). Ein Sync im Hotspot
  ohne Akku über 50 % wird mit `SyncAbgebrochen("regel")` beendet, wenn die
  Regel das nicht mehr erlaubt (heute prüft `sync` das beim Start des Syncs;
  ob es auch während des Syncs neu bewertet wird, steht in `sync.py` zu prüfen).

---

## 4. Leise-Zeiten

Ist `ruhe` in `ZustandMelden` (`events.py`) gesetzt, hat `led.py` die Zustände
schon als Eingabe, nutzt sie aber nicht. Aufwachen-Lauflicht (warmweiß, 25 %
Deckel) läuft heute bei jedem `Bereit`, auch nachts.

| Zustand `ruhe` | Ton `lader` | Ring |
|---|---|---|
| `normal` | spielt, Pegel wie ein Hinweiston (`hinweis_pegel`, Vorgabe 15, Untergrenze 10), nicht wie die Hörlautstärke der Sitzung | „lädt“, 15 % (heutiger Wert) |
| `leiser` | **kein Ton** (Empfehlung; sonst nur mit der kleinsten Fenster-Grenze) | „lädt“ gedimmt, Vorschlag 5 % |
| `stumm` | **kein Ton** (nicht auf `hinweis` abgebildet) | „lädt“ gedimmt, Vorschlag 3 %; Lauflicht „Aufwachen“ aus |
| Zeit nicht vertrauenswürdig (`zeit_ok` falsch) | höchstens `leiser`-Verhalten, also kein Ton | gedimmt |

Zwei Stolperstellen:

* **Regel 2 in `core-interface.md` 6.2:** Heute wird jeder Ton aus der Liste
  unter „stumm“ durch `hinweis` ersetzt. Für `lader` soll er **entfallen**. Sonst
  weckt das Andocken nachts doch mit einem leisen Piep. Das ist ein
  Vertragseingriff.
* **Leerer Akku und Zeit:** Wer eine leere Box andockt, hat keine
  vertrauenswürdige RTC (`power.py`, `RTC_FRUEHESTENS`), bis NTP die Uhr setzt.
  Dann gilt „leiser“ ohne „stumm“. Die Rückmeldung kommt aber im Moment `Bereit`.
  Empfehlung: Ton erst, wenn `zeit_ok` stimmt oder nach 10 s Wartezeit
  ohne Zeit **gar kein Ton** (Ring weiter gedimmt). So gibt es nachts keinen
  Ausrutscher.

Ton `lader` nutzt die Lautstärke der Sitzung (`lautstaerke_start` aus der
Konfiguration): nach einem Start ist das die Startlautstärke, nicht die vom
Abend. Auch deshalb: Pegel wie `hinweis` (`sounds.pegel`), nicht wie `start`.

---

## 5. Unterwegs: Folge von R10 („jede Stromquelle ist ein Lader“)

Fakten aus dem Code: Der Lader-Zustand kommt allein aus
`battery_power_plugged` des PiSugar (`power.py`, `PiSugarStrom.lader`). Der
PiSugar sieht nur „Strom am Eingang“, nie die Quelle. Das war schon vor R10 so;
neu ist, dass es nur noch eine Buchse gibt und jede Quelle den Start auslöst.

### 5.1 Was heißt „jede Quelle weckt die Box“?

* Powerbank in der Tasche, Auto-Buchse beim Anlassen, fremdes Netzteil bei
  Oma: Die ausgeschaltete Box startet, zeigt „lädt“ (Ton, Ring), prüft den
  Sync, geht nach `LADER_KURZ_S` wieder aus. Im Auto bei schlafendem Kind ist das
  der Fall für die Leise-Zeiten (Uhrzeit-Fenster) und nicht für „nachts im
  Auto“ (tagsüber im Auto kein Fenster, also Ton).
* **Wiederholtes Wecken:** Autos mit schaltbarer Buchse und Powerbanks, die bei
  kleiner Last abschalten, geben Strom „neu“. Jedes Mal startet die Box wieder:
  Ton, Ring, Start (Akku und SD-Karte belastet, Startvorgänge). Nicht
  belegt, wie oft das praktisch passiert; am Muster mit einer echten Powerbank
  und einem Autoladegerät beobachten (T5 erweitern).
* Eine Box, die **schon läuft**, bekommt nur die Rückmeldung (Punkt 3).

### 5.2 Hotspot-Regel (`syncregel.py`, `box-software.md` „Netz, Sync, Strom“)

Heute: `hotspot`: erlaubt, wenn Lader dran **oder** Akku über 50 %. Gedacht war:
Lader heißt genug Strom für einen großen Sync. Jetzt heißt „Lader“ auch
„Powerbank im Auto“, und der Start-Sync (`start_lader`) läuft **bei jedem
Anstecken** los, im Handy-Hotspot, ohne Datenbegrenzung (Entscheidung C). Das
kann unbemerkt viel Mobilfunkvolumen kosten, sobald das Handy im Auto den
Hotspot an hat.

**Vorschlag:** `SyncStarten("start_lader")` darf nur im Netz `home` laufen. Der
Takt-Sync und der HA-Knopf behalten die bestehende Regel (Hotspot mit Lader
oder Akku über 50 %). Umsetzung: ein Parameter `grund` in `sync_erlaubt` oder
in `sync.regel_erlaubt`. Vertrag: `SyncStarten` / Zeile in `core-interface.md`
(„`sync` entscheidet nach der Netz-Regel“).

### 5.3 Updates

Bedingung `home` bleibt (`idle._update_bedingung`: `klasse == "home"`, am Lader,
spielt nicht, kein Sync). Auswirkung der neuen Lage: Eine Powerbank im Heimnetz
erfüllt „am Lader“ ebenso. Das ist unproblematisch (Rollback bei Fehler ist
im Design, CUJ 10). Ein Strom-Aus mitten im Update (Powerbank leer) ist der
Fall, den der Rollback schon abdeckt.

Neu und wichtig für CUJ 10: Das Update setzt voraus, dass die Box läuft. Mit
dem Kurz-Zähler hat Tobias nach dem Andocken nur noch etwa 2 min. Wege:
(a) HA-Befehl `HaUpdateAnstossen` beendet den Kurz-Modus (Punkt 2),
(b) Knopf kurz „wach halten“. HA-Befehle sind **nicht** retained
(`mqtt-v1.md`: `cmd`, QoS 1, nicht dauerhaft, mit Ablaufzeit). Ein Befehl an eine
ausgeschaltete Box geht verloren. Siehe Entscheidung 6.

### 5.4 Abschalten

* Kurz-Modus gilt auch unterwegs. Wer im Auto die Powerbank ansteckt und einen
  Tobie auflegt, bleibt am Laufen (Abbruch durch Tobie). Wer nur ansteckt, dessen
  Box geht nach 2 min wieder aus. Das ist stimmig.
* **Normale 20-min-Regel am Lader:** `idle._update_bedingung` und die Regel
  „am Lader erst abschalten, wenn Sync und Update fertig“ ändern sich nicht.
* `AkkuTiefstand` wird am Lader ignoriert (`idle.py`). Eine schwache Powerbank,
  die weniger liefert als die Box zieht, hält die Box „am Lader“ bei fallendem
  Akku. Nicht belegt, wie der PiSugar 3 Plus an 5 V/1 A reagiert. Hinweis: Der
  PiSugar meldet nur „Netzteil steckt“, nicht „Netzteil reicht“. Am Muster mit
  einer 1-A-Quelle prüfen (unter Last lädt der Akku nicht, `battery_charging`
  vs. `battery_power_plugged`).

### 5.5 Sockel und Kabel unterscheiden?

Vorschläge, nichts entschieden:

| Weg | Funktioniert? | Bewertung |
|---|---|---|
| **Netz:** Heim-WLAN (`home`) heißt daheim | Software, kein Bauteil. Aber: erst nach 10 bis 20 s bekannt, und „Powerbank daheim“ sieht aus wie Sockel | gut genug für die Regeln, die ohnehin `home` verlangen (Update, Start-Sync). Für die Rückmeldung zu spät |
| **Spannung/Strom** am PiSugar-Eingang | nicht belegt. Der Sockel liefert 5,1 V aus einem Raspberry-Pi-Netzteil, eine Powerbank 5,0 V, die Streuung ist größer als der Unterschied | **nicht tauglich**, nicht weiter verfolgen |
| **Verlauf:** Sockel-Start tritt nur auf, wenn der Merker „war am Lader“ stimmt (Punkt 1) | nein, siehe Tabelle in Punkt 1 | nicht tauglich |
| **Mechanisch:** ein winziger Taster oder Hallsensor in der Nut/Tasche der Box, den die Sockelrippe oder die Mulde schließt, an einem GPIO | ja, braucht ein Bauteil (< 1 €) und die Box-Mechanik. Der Sockel bleibt ohne Elektronik (R9), nur eine Rippe drückt. Lesbar ab Start | **sicherste Lösung**, aber Hardware-Änderung. Nur, wenn die Software-Regeln nicht reichen |

**Vorschlag:** Erst ohne Unterscheidung bauen (Punkt 5.2: Start-Sync nur
`home`; Rückmeldung wie am Sockel; Kurz-Modus für alle Quellen). Den Schalter nur
nachrüsten, wenn der Test mit Powerbank und Auto stört.

---

## 6. Wegfall des Pololu #5398

Software-Folgen: **keine.** Geprüft:

* `grep` nach `5398`, `Ideal-Diode` in `box/`, `docs/designs/`,
  `docs/protocol/`, `docs/data-model.md`, `docs/betrieb/`: kein Treffer.
* Der Lader-Zustand kommt allein aus `battery_power_plugged` des PiSugar
  (`power.py`). Der #5398 hat kein Signal an den Pi geliefert.
* Mit zwei Eingängen gab es auch vorher nur das Wissen „irgendwo Strom“.

Nur Pläne und Texte sind betroffen (Punkt 7, Art Plan). Zu prüfen am Muster, nicht
in der Software: Ob `battery_power_plugged` weiter `true` meldet, wenn die
einzige Buchse direkt am PiSugar-Eingang hängt (ohne Diode). Das ist die Annahme
von R10; mit dem Muster bestätigen (T4/T5).

---

## 7. Betroffene Verträge und Design-Stellen

**Verträge nur benannt, nicht geändert.** „I“ = inhaltliche Änderung, „K“ =
Klarstellung im Text, „O“ = optional.

| Datei | Abschnitt | nötige Änderung | Art |
|---|---|---|---|
| `docs/protocol/core-interface.md` | 3.3, Ereignis `Bereit` (Zeile ~177) | Feld „Einschalten“ (`neu_gestartet: bool`), damit `idle` Start und Dienst-Neustart trennt, und spielt der Kern den Start-Ton nur dann, wenn kein Lader-Ton kommt (I) | Vertrag |
| `docs/protocol/core-interface.md` | 3.6, `LaderGeaendert` (Zeile ~207) | Bedeutung „irgendeine Stromquelle am Eingang“; Rückmeldung mit Sperre 10 s; Spalte „Bedeutung“ ist leer (K) | Vertrag |
| `docs/protocol/core-interface.md` | Befehle, neu | neuer Befehl `LaderMelden(art: "start"\|"angedockt"\|"abgezogen")` für den Ring (I) | Vertrag |
| `docs/protocol/core-interface.md` | `TonSpielen` (Zeile ~295) | neuer Ton `lader` in der Liste (I) | Vertrag |
| `docs/protocol/core-interface.md` | 6.2 Konfliktregeln, Regel 2 | `lader` unter „stumm“ **entfällt** statt `hinweis`; unter „leiser“ ebenso (I) | Vertrag |
| `docs/protocol/core-interface.md` | `SyncStarten` (Zeile ~301) | `start_lader` nur im Netz `home` (I) | Vertrag |
| `docs/protocol/core-interface.md` | Tabelle der Teilautomaten, Zeile `idle.py` (~338) | Eingänge ergänzen (`Hauptknopf` kurz im Kurz-Modus ist schon Eingang); Ausgänge `LaderMelden`, `TonSpielen`; Zustand Kurz-Modus (I) | Vertrag |
| `docs/protocol/core-interface.md` | `ZustandMelden.strom` (Literal) | optional neuer Wert `lader_start`, wenn der Merker als Zustand sichtbar sein soll (O) | Vertrag |
| `docs/protocol/core-interface.md` | 11 Konstanten | `LADER_KURZ_S` (120), `LADER_NETZ_WARTE_S` (45), `LADER_MELDUNG_SPERRE_S` (10) (I) | Vertrag |
| `docs/protocol/core-interface.md` | Bedingungen `HaUpdateAnstossen` (Zeile ~1086) | Text bleibt; „Lader an“ meint jetzt jede Quelle (K) | Vertrag |
| `docs/protocol/mqtt-v1.md` | Statusfeld `lader` (Zeile ~152) und Entität `lader` (~595) | Hinweis: „Strom am Eingang, jede Quelle“; Feldname bleibt (K) | Vertrag |
| `docs/protocol/ha-websocket-v1.md` | Aktion 22 `tobibox/box/sync` (Zeile ~932) | Text „Hotspot nur mit Lader oder über 50 %“ bleibt; Zusatz, dass der automatische Start-Sync nur im Heimnetz läuft (K) | Vertrag |
| `docs/data-model.md` | Töne (Datei `box/sounds/`, `hinweis_pegel`) | Ton `lader.wav` mit Pegelregel wie `hinweis` (I) | Vertrag |
| `docs/data-model.md` | `lauf.json` | nur nötig, wenn der Merker „am Lader beim Ausschalten“ gewünscht ist (laut Punkt 1 nicht empfohlen) (O) | Vertrag |
| `docs/designs/box-software.md` | CUJ 10 „Software-Update“ | Hinweis: Fenster nach dem Andocken nur etwa 2 min, Knopf kurz oder HA-Befehl hält wach | Design |
| `docs/designs/box-software.md` | CUJ 16 „Leerlauf-Abschaltung“ | Start am Lader: Rückmeldung, Sync, Kurz-Zähler; Wecker-Satz am Ende bleibt | Design |
| `docs/designs/box-software.md` | Baustein 3 Nr. 4 „Strom / Leerlauf“ (Tabelle ab ~Zeile 1323) | neue Zeilen aus Punkt 2.2; Zeile „beim Start | am Lader“ ersetzen | Design |
| `docs/designs/box-software.md` | „Netz, Sync, Strom“ (Zeile ~1644) | Start-Sync nur `home`; „Lader“ = jede Quelle | Design |
| `docs/designs/box-software.md` | Update, Bedingungen (~1684) | Klarstellung „Lader“ | Design |
| `docs/designs/box-software.md` | Abschnitt LED-Ring / CUJ 18 (~841) und AP 4.1 (~2731) | Zustand „Laden“, Dimmen nach `ruhe`, Aufwachen-Lauflicht unter Leise-Zeit aus | Design |
| `docs/designs/box-software.md` | CUJ 15 „Leise-Zeiten“ | Zeile zu Ton `lader` und Ring | Design |
| `docs/designs/box-software.md` | CUJ 20 | Satz zu Start am Lader mit liegendem Tobie (je nach Entscheidung 4) | Design |
| `docs/designs/box-software.md` | Abschnitt PiSugar-Wecker (AP 4.3, ~2756) | `auto_power_on` ergänzen; Wecker-Beschreibung abgleichen | Design |
| `docs/betrieb/pisugar-wecker.md` | Abschnitt 4 und 6 | „Auto-Power-On“ und Lücke Start-Sync ohne Netz | Plan |
| `docs/plan/stueckliste-und-psp.md` | 5.5.2 (Zustände LED) | Zustand „Laden“ ergänzen | Plan |
| `docs/plan/stueckliste-und-psp.md` | 5.6.3 / 5.6.5 | 5.6.3: Kurz-Zähler; 5.6.5: „Auto-Power-On aus“ wird „an“ | Plan |
| `docs/plan/stueckliste-und-psp.md` | 5.7 | Ton und Ring bei Start am Lader | Plan |
| `docs/plan/stueckliste-und-psp.md` | 8.2.4 | Test „Andocken weckt nicht“ wird T5 aus Rev. 4 (Andocken weckt kurz) | Plan |
| `docs/plan/stueckliste-und-psp.md` | Punkt 3, 7, 3.2.5, Stückliste 1.1 (#5398) | schon in Rev. 4 Abschnitt 7.1 vermerkt | Plan |
| `box/src/tobibox/idle.py` | `_start_pruefung`, `_auswerten`, `LEERLAUF_S` | Kurz-Modus, Frist-Funktion, Netz abwarten, Abbruchregeln | Code |
| `box/src/tobibox/power.py` | `intervall_s`, `pruefe` | schnelle Lader-Abfrage (1 bis 2 s); Rückmeldungssperre | Code |
| `box/src/tobibox/led.py` | `ZUSTAENDE`, `LedLogik.beobachte`, `_aufwachen`, `_akku` | Zustand `laden`; Helligkeit nach `ruhe`; Aufwachen bei `Bereit` nicht nachts; `LaderMelden` annehmen | Code |
| `box/src/tobibox/sounds.py` | `pegel` | Ton `lader` mit Pegel wie `hinweis` | Code |
| `box/src/tobibox/core.py` | `_TOENE_UNTER_STUMM` (Zeile 43), Regel 2 | `lader` wegfallen lassen statt `hinweis` | Code |
| `box/src/tobibox/session.py` | `_bereit` (Zeile ~818) | kein `start`-Ton, wenn Lader-Start (sonst zwei Töne) | Code |
| `box/src/tobibox/syncregel.py`, `sync.py` | `sync_erlaubt` | Parameter `grund`, Start-Sync nur `home` | Code |
| `box/src/tobibox/app.py` | `_sim_strom`, Befehlsverteiler (~Zeile 400), `_sync_starten` | `LaderMelden` an `led` und `sounds`; `neu_gestartet` an `Bereit` | Code |
| `box/src/tobibox/quiet.py` | – | keine Änderung (`ruhe` kommt schon in `ZustandMelden`) | Code |
| `box/tests/unit/` | `test_idle.py`, `test_led.py`, `test_power.py`, `test_sounds` (hier `test_app_toene.py`), `test_core*.py`, `test_syncregel`-Fälle in `test_power.py` | neue Fälle je Zeile aus 2.2 und 4 | Code |
| `box/tests/cuj/` | `test_cuj16_leerlauf.py` (laut Design vorgesehen, noch nicht vorhanden), `test_cuj10_update.py` | CUJ 16 mit Kurz-Modus; CUJ 10 mit Fenster | Code |

**Zahl der betroffenen Vertragsstellen: 14** (davon 9 inhaltliche Änderungen,
4 Klarstellungen, 1 optional). Zusätzlich 8 Stellen in `box-software.md` und
5 in Plan-Dokumenten.

---

## 8. Offene Entscheidungen für Tobias

1. **Startgrund nicht erkennen, Ablauf gutmütig machen?** Empfehlung: ja
   (Punkt 1). Jeder Start mit Strom am Eingang gilt als „am Lader“. Kein
   Merker in `lauf.json`.
2. **Kurz-Zähler 120 s?** (Alternative 60 s, nur sicher bei „Andocken“; 300 s
   für mehr Reserve.) Empfehlung: 120 s ab Ende der Rückmeldung, Sync hält.
3. **Was beendet den Kurz-Modus?** Empfehlung: Tobie auflegen, Hauptknopf kurz,
   Abziehen, HA-Befehl. Nicht: Weiter, Zurück, Drehregler.
4. **Liegender Tobie beim Start am Lader (CUJ 20):** spielen oder nicht?
   Empfehlung: CUJ 20 unverändert (spielt, nachts schützt „stumm“). Dann bleibt
   „ohne Wiedergabe“ aus R8 nur für den Normalfall wahr. Alternative: am Lader
   nie von selbst spielen (Abheben und Auflegen nötig), widerspricht dem Zweck
   von CUJ 20 bei einem Knopfstart.
5. **Leise-Zeiten:** Kein Ton unter „leiser“ **und** „stumm“, Ring gedimmt
   (5 % / 3 %), Lauflicht „Aufwachen“ nachts aus? Empfehlung: ja.
6. **Update-Fenster:** Reicht „Knopf kurz oder HA-Befehl hält wach“, oder
   soll HA einen Wunsch „Update beim nächsten Andocken“ vormerken? Empfehlung:
   erst das Einfache; Vormerken nur, wenn Tobias das Update oft aus HA
   anstoßen will.
7. **Unterwegs: Start-Sync nur im Heimnetz?** Empfehlung: ja (Punkt 5.2).
   Takt-Sync und HA-Knopf bleiben bei der Hotspot-Regel.
8. **Andocken bei laufender Box: ebenfalls Sync prüfen?** Empfehlung: ja, einmal
   je Andocken, mit der Sperre (10 s) und nur im Netz `home`.
9. **Rückmeldung bei spielendem Hörspiel:** nur Ring, kein Ton?
   Empfehlung: ja.
10. **Sockel/Kabel unterscheiden (Taster in der Box)?** Empfehlung: jetzt nicht,
    erst nach Test mit Powerbank und Auto.
11. **Frühstart-Ring (blau in den ersten Boot-Sekunden)?** Empfehlung: erst
    messen, ob die 20 bis 30 s stören.

---

## 9. Grober Aufwand und Reihenfolge

| # | Paket | Modell | Inhalt |
|---|---|---|---|
| 0 | **Muster-Test T5 vorziehen** (Tobias, Hardware) | – | Schalter „Einschalten bei Strom“ finden und bestätigen (`config.json`, `help xx`, Web-Oberfläche); Boot-Schleife am Sockel (Box mit Strom herunterfahren: bleibt sie aus?); Wecken mit Powerbank/Auto; Zeit bis Ring/Ton messen; `battery_power_plugged` an der einzigen Buchse |
| 1 | Doku-Abgleich nach Entscheidung (Design, Plan, `pisugar-wecker.md`) | Haiku | Tabelle in Punkt 7, Art Design und Plan |
| 2 | Vertragsvorschläge als Diff für Tobias | Haiku | nur Art Vertrag, Tobias nimmt an |
| 3 | `idle.py` Kurz-Modus und Tests (`test_idle.py`) | Sonnet | Punkt 2, mit simulierter Uhr |
| 4 | `power.py` schnelle Abfrage, Sperre, Tests | Sonnet | Punkt 3 |
| 5 | `led.py` Zustand Laden, Dimmen, Aufwachen nachts, Tests | Sonnet | Punkt 4 |
| 6 | Ton `lader` (`sounds.py`, `core.py` Regel 2, `session.py`, Ton-Datei über `make_sounds`, Lautheit) | Sonnet (Datei erzeugen: Haiku) | Punkt 4 |
| 7 | Start-Sync nur `home` (`syncregel.py`, `sync.py`) | Sonnet | Punkt 5.2 |
| 8 | CUJ-Tests 16 und 10 (Simulation) | Haiku | Tabellen aus 2.2 |
| 9 | Pi-Probelauf: Zeiten, Powerbank, Auto, Nachtfenster | Tobias | Abnahme von R8 |

Reihenfolge: 0 zuerst (klärt Punkt 1 und die Boot-Schleife, die alles andere
kippen könnte), dann 1 und 2 nach Tobias' Entscheidungen, dann 3 bis 7 (3 und 4
unabhängig, 5 und 6 danach), 8, 9. Nichts davon blockiert die Mechanik der
Ladestation (T1, T2).
