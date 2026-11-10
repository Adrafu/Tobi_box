# Ein- und Ausschalten: Design-Entwurf Rev. 2 (EGM Schritt 2, nach Resolve)

*   **Datum:** 10.11.2026
*   **Status:** Rev. 2, zur Freigabe durch Tobias. Nichts umgesetzt; kein Vertrag, kein Design, kein Plan, kein Code geändert.
*   **Verbindlich:** `resolve.md` (R1 bis R7 von Tobias, P1 bis P12 der Projektleitung). Befunde: `review_software.md` (G1 bis G15),
    `review_hardware.md` (H-G1 bis H-G15); Abschnitt 11 sagt zu jedem, was daraus wurde.
*   **Weitere Grundlage:** `concepts_brief.md` (E1 bis E14), `research.md`, `docs/egm/ladestation/software_folgen.md` Abschnitt 10 (S1 bis S11),
    ruhender Entwurf `docs/egm/start-am-lader/design_draft.md`. Bestand: `docs/designs/box-software.md`, `docs/protocol/*`, `docs/data-model.md`,
    `docs/plan/stueckliste-und-psp.md`, `firmware/tobibox-reader/`, `box/src/tobibox/`.
*   **Zeichen:** [Schätzung] = nicht gemessen. „Muster“ = Breadboard oder Probeaufbau mit PiSugar. Im Code heißt ein Tobie `figur`.
*   **Namen:** *Spielt* = Pi-Zustand `aktiv` (`idle.py:105-107`), *Bereit* = `leerlauf` (nichts wird gespielt, Dienst läuft), *Aus* = Pi stromlos.
    Die technischen Namen in `ZustandMelden.strom` bleiben (`core-interface.md:320`).

---

## 0. Kurzfassung und was sich gegenüber Rev. 1 geändert hat

1.  **Drei Zustände, wenige Regeln.** Bereit läuft ohne Frist, solange Strom am Eingang liegt; sonst 10 min nach dem letzten Spielen oder Bedienen, dann Aus.
2.  **Der ESP32 ist der Wächter** (Akku-Pad BAT, Tiefschlaf). Weckquellen: Tobie (LPCD, **nur im Zustand Aus**), Tonie-Magnet (Hall-Schalter im Deckel), `STROM_IN`, Hauptknopf (über den PiSugar).
    Er drückt Pad 10 nur bei fehlenden 5 V und zeigt sofort das Lauflicht.
3.  **Wecken nur bei Änderung** (R3, R6): Ein Tobie, der seit dem Ausschalten unverändert liegt, weckt nie. Abheben und neu Auflegen weckt.
4.  **Ring: Hardware-Weiche statt Muster-Befehlen** (R1). Der ESP32 zeigt nur das Lauflicht beim Wecken; sobald der Dienst bereit ist, schaltet er die Weiche auf den Pi.
    `led.py` bleibt, `RING`-Muster, `br2`, `per`, `frame`, Gleichheitstest und die doppelte Musterlogik **entfallen**.
5.  **LPCD in Bereit entfällt** (R2). Der Leser fragt in Bereit wie heute ab.
6.  **Lader-Ton** (R4) bleibt, mit Regeln aus S5, S9 und Entscheidung L; Abschnitt 6.3 prüft den Doppel-Ton-Fall.
7.  **`STROM_IN` ist Pflicht** (P1). Neuer Pinplan nach dem echten SuperMini-Pinout (P11, Abschnitt 5.6).
8.  **Verträge in zwei Schritten** (P8): Schritt 1 sofort (Frist, Strom, Lader-Ton, Frühton, `STROM_IN`-Wert, **19 Stellen**), Schritt 2 nach den Messungen (`WAKE`, `SLEEP`, `CFG`, `RING_PI`, **15 Stellen**). Abschnitt 8.
9.  **Kürzer:** Wegfall von `RING`-Muster, `wring_s`-Uhr im ESP32, `wach`, `SLEEP_OK`, `dur`, `boot_id` in der Frühton-Marke; zusammengelegte Zeilen der Übergangstabelle.
10. **Typischer Tag ohne Sockel [Schätzung]:** 8,2 bis 10,0 Wh von 15 Wh (Abschnitt 7).

---

## 1. Zustandsmodell

### 1.1 Die drei Zustände

| | **Spielt** | **Bereit** | **Aus** |
|---|---|---|---|
| Pi, `tobiboxd`, MPD | laufen | laufen | aus (PiSugar 5 V aus) |
| Verstärker | an | aus (Overlay hält SD_MODE, `stueckliste-und-psp.md:50-54`) | stromlos |
| Ring | läuft / Gute Nacht | **dunkel, MOSFET aus**; kurzes Aufleuchten (1.3) | stromlos |
| Leser | Dauerabfrage 200 ms (`timing.h:9`) | **Dauerabfrage wie heute** (R2) | PN5180 im LPCD, Hall scharf, ESP32 im Tiefschlaf |
| Leistung [Schätzung] | 1,6 bis 1,9 W | 1,0 bis 1,3 W | 0,001 bis 0,007 W |
| Frist | – | 10 min ohne Strom, sonst keine | – |

### 1.2 Übergänge

„Strom“ = Strom am Eingang des PiSugar aus **irgendeiner** Quelle. Quellen: `STROM_IN` über den Leser (maßgeblich, wenn die Firmware es meldet) und `pisugar-server` (`power.py:155-162`). Widersprechen sie sich,
gilt der Leser; der Widerspruch wird protokolliert. „Unbekannt“ (keine Quelle antwortet) gilt nach `STROM_UNBEKANNT_S` = 60 s als **kein Strom** (P1); bis dahin löst es nichts aus.

**Aus verlassen**

| # | Auslöser | Bedingung | Aktion | Folge |
|---|---|---|---|---|
| Z01 | **Tobie aufgelegt** (LPCD) oder **Tonie-Magnet** (Hall) | `tobie=1`, **Lage neu** (4.2), kein Tiefstand | ESP32: Pad-10-Regeln (4.3), Lauflicht, `WAKE reason=tobie\|magnet`; Pi bootet | Hochfahren, dann **Spielt** (unter „stumm“: Bereit, CUJ 15) |
| Z02 | **Hauptknopf** | – | PiSugar schaltet ein; ESP32 sieht 5 V (VBUS), Lauflicht | Hochfahren, dann **Bereit** (liegt ein Tobie: Spielt, CUJ 20) |
| Z03 | **Strom kommt** (Andocken R8, Kabel, Powerbank) | `STROM_IN` steigt, VBUS tief | ESP32 pulst Pad 10 (4.3), Lauflicht, `WAKE reason=strom`; nach `Bereit` Ring Ladestand 5 s, Sync prüfen (S8) | Hochfahren, dann **Bereit** ohne Frist (liegt ein Tobie: Spielt) |
| Z04 | **Strom liegt beim Einschlafen an** (Strom kam während des Herunterfahrens; Hauptknopf lang am Sockel, E4) | `STROM_IN` hoch, VBUS seit 3 s tief | ESP32 schläft nicht, sondern wie Z03 | wie Z03 |
| Z05 | Tobie nach Tiefstand | `tobie=0` (Pi setzte es vor dem Tiefstand-Aus) | nichts; nur Z02 bis Z04 wecken | **Aus** |
| Z06 | Hochfahren fertig (`Bereit`) | – | Frist beginnt; Frühton-Marke verbraucht (6.2); Pi übernimmt den Ring (3.3) | **Bereit** / **Spielt** |

**Spielt oder Bereit verlassen**

| # | Auslöser | Bedingung | Aktion | Folge |
|---|---|---|---|---|
| Z07 | Folge zu Ende, Pause, Abheben, „stumm“ beginnt, Gute Nacht zu Ende | – | Zeiger speichern; Ring wie 1.3; Frist 10 min ab jetzt, falls kein Strom | **Bereit** |
| Z08 | **Herunterfahren:** Hauptknopf lang (immer), Frist um (kein Strom; kein Lernmodus, Sync, Update), Akku-Tiefstand (kein Strom, bricht den Sync ab, Ton `akku_leer`, `CFG tobie=0`) | – | Zeiger speichern, Ring aus, `SLEEP hell_ab hell_bis` (3.2), `poweroff` (`idle.py:252-259`) | → **Aus** |
| Z09 | Frist um, Lernmodus / Sync / Update läuft | – | warten, danach sofort prüfen (Lernmodus: Frist neu, `idle.py:238-242`) | **Bereit** |
| Z10 | **Dienst-Neustart** (Update, Absturz) | gleiche Boot-ID (`bootid.py:3-4`, `lauf.py:6-9`) | ESP32 bleibt wach; Zustand wie vor dem Neustart; liegender Tobie spielt nicht von selbst; **Start-Ton klingt wie heute** (`session.py:844-845`, Entscheidung G, P5); keine Lader-Rückmeldung; kein Wecken | gleich |
| Z11 | Tobie aufgelegt / Hauptknopf kurz (nur Bereit) | nicht „stumm“ | Dauerabfrage → Hörspiel, Ziel ≤ 3 s | **Spielt** |
| Z12 | Bedienung (Knopf, Weiter, Zurück, Drehregler, Kopfhörer) | – | Frist neu (`idle.py:186-190`); Ring 3 s | **Bereit** |
| Z13 | **Strom kommt** bei laufender Box | Wechsel „kein Strom“ nach „Strom“ **nach** der ersten bekannten Messung (6.3) | Frist verworfen; Rückmeldung nach 6.3 (Ring, Ton `lader`, Sync einmal je Andocken, S8) | **Bereit** ohne Frist / **Spielt** |
| Z14 | **Strom weg** | – | Ring Akku 5 s, kein Ton; Frist 10 min **ab jetzt** (E9); Tiefstand wieder scharf | **Bereit** mit Frist |
| Z15 | Herunterfahren wirkt nicht (`HerunterfahrenFehlgeschlagen`, B1) | `poweroff` meldet Fehler | Hinweis an HA, Frist neu (`idle.py:322-343`); ESP32 bricht nach `SLEEP_WARTEN_S` ab (`ERR sleep_aborted`) | **Bereit** |

### 1.3 Regeln, die quer durch die Tabelle gelten

*   **Frist = `LEERLAUF_S` = 600 s** (heute 1200, `idle.py:57`). Sie zählt, wenn nichts gespielt wird, auch mit liegendem Tobie (Entscheidung O, `box-software.md:532-537`), und **nur ohne Strom**.
    Heute zählt sie auch mit Strom (`idle.py:211-232` prüft den Strom nicht); das ändert sich in Schritt 1.
*   **Bedienung** setzt die Frist neu, HA-Befehle nicht (`idle.py:12-14`). Leise-Zeiten ändern nie den Zustand; Z07 und E5 gelten gleich: unter „stumm“ ohne Sockel geht die Box nach 10 min aus.
*   **Ring in Bereit** (E6, Vorschlag aus dem Brief): dunkel. Es leuchtet auf: 3 s nach Bedienung, Auflegen, Abheben; 5 s Akku nach Andocken und Abziehen; 10 s Pause nach Z07 bei liegendem Tobie; Lernmodus dauernd.
    Das ändert `led.py:270-271` (heute zeigt der Ring in `leerlauf` mit liegendem Tobie dauernd Pause). Während „Gute Nacht“ läuft, zeigt die Akku-Anzeige 5 % statt 15 % (G13).
*   **Zeitziele** (P9): Auslöser → Lauflicht so schnell, wie die Messung erlaubt, **Ziel unter 1,5 s** (Messziel, kein Tor). Bereit → Hörspiel ≤ 3 s. Aus → Hörspiel ≤ 10 s (Rückfall 15 s, E13). Details 6.1.
*   **Ein Fehlimpuls** an Pad 10 darf ein laufendes Hörspiel nie pausieren: Regeln 4.3.

---

## 2. CUJs

Neu sind CUJ 21 bis 25. Geändert sind CUJ 10, 15, 16, 18, 20.

**CUJ 21: Hochfahren mit sofortigem Lauflicht.** *Given* Box aus. *When* Tobie aufgelegt, Magnet erkannt, Hauptknopf, oder Strom kommt.
*Then* (1) Der ESP32 zeigt das weiße Lauflicht (tags normal, nachts gedimmt, 3.2). (2) Der Frühdienst spielt `start`, sobald ALSA da ist (Ziel ≤ 5 s nach 5 V am Pi), nur im Modus „normal“ bei sicherer Uhr (6.2).
(3) `Bereit` (Ziel ≤ 8,5 s) übernimmt den Ring und spielt keinen zweiten Start-Ton. (4) Liegt ein Tobie, spielt er (CUJ 20); unter „stumm“ gilt CUJ 15; Hörspiel ≤ 10 s nach dem Auflegen.
*Ausnahme Pi kommt nicht hoch:* Kein `PING` binnen `WECK_LAUFLICHT_MAX_S` (30 s): Lauflicht endet, Ring dunkel, `ERR host_timeout`, ESP32 geht in `OHNE_HOST` (4.1). Zwangs-Aus: E10.

**CUJ 22: Tobie weckt die ausgeschaltete Box.** *Given* Box aus, `tobie=1`. *When* ein Tobie wird aufgelegt. *Then* Tonie: Hall-Schalter meldet den Magneten; Karte: LPCD meldet eine Feldänderung, eine Lesung bestätigt (Hand, Metall wecken nicht).
Danach CUJ 21. **Nur eine Änderung weckt (R3):** Lag der Tobie schon beim Ausschalten, weckt er nie; Abheben und neu Auflegen weckt; ein anderer Tobie weckt. Der Hauptknopf weckt immer.
Karten ohne Magnet wecken nur über LPCD; trägt LPCD nicht (Messung M4), weckt für Karten nur der Hauptknopf.

**CUJ 23: Box steht am Sockel bereit.** Strom am Eingang: Bereit ohne Frist, Hörspiel ≤ 3 s, nie von selbst aus (Z08 braucht „kein Strom“). Das gilt auch, wenn `pisugar-server` hängt, weil `STROM_IN` den Wert liefert (P1).
Kommt der Strom, während die Box herunterfährt, startet sie wieder (Z04).

**CUJ 24: Pause ohne Sockel, nach 10 min aus.** Nichts gespielt, nichts bedient, kein Lernmodus/Sync/Update, kein Strom, 10 min: Zeiger gespeichert, `SLEEP`, Herunterfahren, ESP32 schläft.
Wird in den 10 min ein Tobie aufgelegt, spielt die Box in ≤ 3 s. Wird während des Herunterfahrens ein anderer Tobie aufgelegt, weckt er danach (4.2, G4).

**CUJ 25: Andocken und Abziehen.**

| Lage | Andocken | Abziehen |
|---|---|---|
| **Aus** | Box startet (CUJ 21), Frühton `start`, nach `Bereit` Ring Ladestand 5 s, Sync prüfen. **Kein** Lader-Ton | – |
| **Bereit** | Ring Ladestand 5 s, **Ton `lader`** (nicht in „leiser“, „stumm“, bei unsicherer Uhr, im Lernmodus), Sync prüfen; Frist verworfen | Ring Akku 5 s, kein Ton, Frist 10 min ab jetzt |
| **Spielt** | nur Ring 3 s (S9); Sync prüfen | nur Ring |
| Update läuft | nur Ring, kein Sync | – |

Sperre `LADER_SPERRE_S` = 10 s für jede Rückmeldung (Ring, Ton, Sync), gerechnet ab der letzten Rückmeldung **oder ab `Bereit`** (6.3). Liegt beim Andocken aus Aus ein Tobie, spielt er (S4, CUJ 20); nachts schützt „stumm“.

**Geänderte CUJs (Wortlaut-Änderung kurz).**
*   **CUJ 16** (`box-software.md:855-868`): „Bereit und Aus“: 10 min ohne **Strom**, sonst bleibt die Box bereit; Strom verwirft die Frist, Abziehen startet sie neu; Hauptknopf (Z02), Tobie/Magnet (Z01) und Strom (Z03, Z04) holen die Box aus Aus.
*   **CUJ 10** (`:789-797`): Am Sockel ist die Box immer bereit; HA kann das Update jederzeit schicken; „Lader“ heißt Strom aus jeder Quelle.
*   **CUJ 15** (`:837-853`): `lader` und Frühton `start` entfallen unter „leiser“, „stumm“, bei unsicherer Uhr. Akku-Anzeige 5 % („leiser“), 3 % („stumm“). Lauflicht beim Wecken: 3.2.
*   **CUJ 18** (`:881-898`): Ring in Bereit dunkel (1.3). Das Lauflicht beim Wecken kommt vom ESP32, danach übernimmt `led.py` über die Weiche (3.3). Deckel 25 % gilt in Pi **und** ESP32.
*   **CUJ 20** (`:919-934`): Zusatz bei *Given* „… oder der Tobie hat die Box geweckt“; die Ausnahme Dienst-Neustart bleibt wörtlich.

---

## 3. Ring mit Hardware-Weiche (R1, R5)

### 3.1 Aufteilung

| Was | Wer |
|---|---|
| Alle Muster, Farben, Zeiten, Leise-Dimmung, Deckel 25 % im Betrieb | **Pi, `led.py`**, unverändert (`led.py:29`, `:182-283`); Bit-Bang auf GPIO 23/24 wie heute |
| Lauflicht beim Wecken (einziges Muster des ESP32) | **ESP32** über einen eigenen SPI-Host (nicht den des PN5180, Plan 8.4.4); Deckel 25 % auch hier |
| Weiche (wer treibt die Ring-Leitungen) und Ring-MOSFET | **ESP32** |
| Wann der Pi übernimmt, und ob der Ring an oder dunkel sein soll | **Pi**, per `RING_PI an=<0\|1>` |

Es gibt **kein** Muster-Protokoll, keinen Keepalive, kein `RING_TIMEOUT_S`. Der ESP32 kann nicht sehen, ob `led.py` noch lebt. Hängt der Pi bei anliegenden 5 V, bleibt der Ring, wie er war; das gilt schon heute.

### 3.2 Helligkeit des Lauflichts (R5)

Tags normal (`RING_WECK_HELL` = 25 %), nachts gedimmt (`RING_WECK_GEDIMMT` = 5 %, Wert nach Messung M14). Der Pi gibt es dem ESP32 vor dem Ausschalten mit:
`SLEEP hell_ab=<s> hell_bis=<s>`. Gemeint: nur im Fenster von `hell_ab` bis `hell_bis` Sekunden **nach dem `SLEEP`** ist es hell, sonst gedimmt.
Der Pi berechnet es aus den Leise-Zeiten (`quiet.py:104`): jetzt tags: `hell_ab` = 0, `hell_bis` = Sekunden bis zum Beginn des nächsten Fensters; jetzt nachts: `hell_ab` = Sekunden bis zum Ende, `hell_bis` = bis zum nächsten Beginn.
Die RTC des ESP32 geht ungenau (RC-Oszillator); deshalb rechnet der Pi mit **10 % Sicherheitsrand** (`hell_ab` später, `hell_bis` früher; Messung M15). Fehlt die Angabe, ist sie abgelaufen oder ist die Uhr unsicher: **gedimmt**. Nach einem Stromverlust des ESP32 ebenso.
Kein `SLEEP` (Hauptknopf lang ohne Dienst, Akku leer) heißt: der alte Wert gilt weiter, wenn er nicht abgelaufen ist.

### 3.3 Übergabe an den Pi

Pi → ESP32 `RING_PI an=<0|1>`, ESP32 → Pi `RING_PI_OK an=<0|1>` (Abschnitt 4.5).

1.  Wecken: ESP32 schaltet zuerst den MOSFET, nach 5 ms beginnt das Lauflicht (H-G8). Die Weiche steht auf „ESP32“.
2.  Der Dienst meldet `Bereit`, `reader` hat `HELLO` mit `caps` `weiche`. `app` sendet `RING_PI an=1` (soll der Ring leuchten, z. B. Hörspiel startet) oder `an=0` (Ring soll dunkel sein, Bereit). Es wird **immer** übergeben, auch bei „dunkel“.
3.  ESP32: beendet das Lauflicht nach dem laufenden Bild, `an=1`: Weiche auf „Pi“, MOSFET bleibt an; `an=0`: Weiche auf „neutral“ (beide Puffer aus, Pull-down am Ring-Eingang), MOSFET nach `RING_AUS_VERZ_MS` aus. Dann `RING_PI_OK`.
4.  `led.py` gibt aus, sobald `RING_PI_OK an=1` da ist. Kommt nichts, wiederholt `app` alle `RING_PI_WDH_S` = 5 s; Bit-Bang auf eine nicht umgeschaltete Weiche ist harmlos.
5.  Wechsel Ring dunkel ↔ leuchtet (Bereit): `app` sendet `an=1` vor dem ersten Bild und `an=0`, wenn der Ring `RING_AUS_VERZ_S` = 2 s dunkel war. `led.py` bleibt bis auf diese Ausgabe unverändert.
6.  Hat `LeserWecken` `ring=1`, spielt `led.py` bei `Bereit` kein eigenes Aufwachen-Lauflicht (`led.py:228-234`) und zeigt gleich den Zustand danach. Das Aufwachen bei `leerlauf→aktiv` ohne Tobie (z. B. HA-Befehl, `led.py:228`) bleibt wie es ist (G13).
7.  **ESP32-Seite bei Fehlern:** Kein `RING_PI` binnen `WECK_LAUFLICHT_MAX_S`: Lauflicht aus, Weiche neutral, MOSFET aus. VBUS weg: sofort (Interrupt, nicht im Takt) Weiche neutral, MOSFET aus (harter Poweroff, H-G8). Neustart des Dienstes: `HELLO` neu, `app` sendet `RING_PI` erneut (idempotent).
8.  **Rollback:** Alter Dienst mit Firmware 2: Das Lauflicht endet nach 30 s, der Ring bleibt dunkel. Neuer Dienst mit Firmware 1.x: ohne `caps` `weiche` sendet er kein `RING_PI`; der Ring hängt dann wie heute am Pi (Hardware-Stand 1 ohne Weiche).

### 3.4 Hardware der Weiche (Anforderungen)

*   Ein Chip mit Freigabe-Eingängen (z. B. 74AHCT125 mit Inverter oder 74AHCT157; Auswahl bei Tobias' Platine). Ein Auswahlsignal `RING_SEL` und die Freigabe: **ESP32**, **Pi** oder **neutral** (Standard bei Reset und Tiefschlaf, durch Pull-down/Pull-up erzwungen). Nie beide Quellen zugleich.
*   Pegel: 3,3 V von ESP32 und Pi, 5 V zum Ring. 330 Ω in Reihe an den ESP32-Eingängen, 10 kΩ nach Masse an den Ring-Eingängen DI/CI (H-G8).
*   Zweiter Teil: Lastschalter-IC statt diskretem High-Side-Aufbau, Abschnitt 5.5.

---

## 4. Leser-Firmware

### 4.1 Zustände des ESP32

| Zustand | Was läuft | Übergänge |
|---|---|---|
| `SCHLAF` | Tiefschlaf (7 µA, `research.md:78`); PN5180 im LPCD (nur wenn `tobie=1`), Hall scharf, Weiche neutral, MOSFET und Pad-Schalter aus, alle Ausgänge gehalten | LPCD-IRQ oder Hall → `PRUEFEN`; `STROM_IN` hoch → `WECKEN` (Z03); 5 V am USB (Knopf) → `WECKEN` |
| `PRUEFEN` | Lage prüfen (4.2); LPCD: PN5180 starten, **eine** Lesung | Lage neu und gültig → `WECKEN`; sonst Bezug nachführen, neu abgleichen, `SCHLAF` |
| `WECKEN` | Pad-10-Puls nach 4.3 (außer bei Knopf: Pi läuft schon), Lauflicht, wartet auf `PING` | `PING` → `LAEUFT`; 30 s ohne `PING` → `OHNE_HOST`; VBUS weg → `SCHLAF` |
| `LAEUFT` | Dauerabfrage (200 ms); `RING_PI`, `CFG`, `SLEEP` | `SLEEP` → `ABSCHALTEN`; VBUS weg ohne `SLEEP` länger als 3 s → `SCHLAF` |
| `ABSCHALTEN` | Dauerabfrage läuft weiter (G4); Ring aus; wartet auf VBUS aus | VBUS weg → Bezug nachmessen → `SCHLAF` oder wecken (4.2); nach `SLEEP_WARTEN_S` = 90 s VBUS noch da → `ERR sleep_aborted`, `LAEUFT` |
| `OHNE_HOST` | Ring aus, kein Tobie-Wecken, wartet | VBUS weg → `SCHLAF`; sonst nichts (E10: Zwangs-Aus nach 120 s) |

*   Der ESP32 merkt, dass der Pi läuft: (1) VBUS-Pegel, (2) offener USB-Port mit `PING` (`reader.py:308`, `:322`, `reader-v1.md:285`). „Pi hängt, 5 V da“ erkennt er nicht (3.1).
*   Er schläft nur, wenn der Pi `SLEEP` gesagt hat **und** VBUS 3 s tief ist, oder VBUS ohne Ansage 3 s tief ist. Nie vor dem Pi.
*   LPCD braucht PN5180-Firmware ≥ 4.0 (`research.md:207`); sonst fehlt `tobie` in `caps`, und für Karten bleibt der Hauptknopf. Viele Platinen haben 3.5; das Update ist Teil von AP E2-3 (Abschnitt 10).

### 4.2 Wecken nur bei Änderung (R3, R6; G1, G4)

*   **Bezug.** Beim `SLEEP` und noch einmal unmittelbar vor dem Tiefschlaf misst der ESP32 die Lage: *kein Tobie*, *Karte/Tonie mit Kennung K* (Lesung) und *Magnet da/weg*. Der Bezug liegt im RTC-Speicher.
*   **Lesen in `ABSCHALTEN`:** Die Dauerabfrage läuft, bis der Pi aus ist. Ändert sich die Lage dabei, gilt: ist sie beim Einschlafen **anders als beim `SLEEP`** und jetzt liegt ein Tobie, wird sofort geweckt (nach 3 s VBUS tief). Das fängt das Kind, das während des Herunterfahrens den Tobie wechselt.
*   **LPCD-Meldung im Schlaf:** eine Lesung. *Leer* → Bezug := leer, neu abgleichen, weiterschlafen. *Gleiche Kennung wie der Bezug* → neu abgleichen, weiterschlafen (Drift). *Andere Kennung, oder Bezug war leer* → wecken. Hand und Metall (ungültige Lesung): nach `LPCD_FALSCH_MAX` = 3 in 10 s Intervall × 4 und Neuabgleich, `ERR lpcd_noise`.
*   **Hall:** Liegt beim Einschlafen der Magnet an, wird der Pin auf „Magnet weg“ scharf gemacht. Kommt diese Meldung, wacht der ESP32 kurz auf (Kurzwach), setzt den Bezug auf *weg* und schärft auf „Magnet da“; dann weckt der nächste Magnet. Der Hall-Schalter weckt **ohne Lesung** (schnell, fremde Magnete zählt M6; Rückfall: Lesung vor dem Puls).
*   LPCD erkennt Abheben nicht zuverlässig (nicht belegt, M4): Für Karten kann ein Abheben deshalb unbemerkt bleiben; dann weckt dieselbe Karte nach dem Wiederauflegen nicht. Das ist die Folge von R3 und hinzunehmen.
*   **Vor jedem Einschlafen** wird LPCD neu abgeglichen (H-G1d) und der PN5180-IRQ gelöscht (4.4).
*   **Strom (P1):** `STROM_IN` weckt bei steigender Flanke. Liegt Strom beim Einschlafen an, schläft der ESP32 nicht (Z04). Das macht „am Sockel nie aus“ unabhängig von „Einschalten bei Strom“ des PiSugar (E4 bleibt als Frage: Hauptknopf lang am Sockel startet die Box dann neu).

### 4.3 Pad 10 (P2; H-G3, H-G4, H-G7)

*   Der ESP32 schaltet Pad 10 mit BAT (Pad 2) zusammen (`research.md:187`) über ein **PhotoMOS-Relais** (5.4).
*   **Nur wenn die 5 V des Pi sicher fehlen:** VBUS tief unmittelbar vor und 10 ms nach der Lesung. **Höchstens ein Puls je Wecken.** Wiederholung frühestens nach 10 s und wieder mit VBUS-Prüfung. Nach einem Reset mit VBUS hoch (Pi läuft) nie pulsen (`WAKE reason=reset`).
*   **Anti-Mistouch bleibt wie ab Werk** (kein Schreiben mehr durch `power.py`). Wirkt ein einzelner kurzer Puls nicht (Messung M1), bildet der ESP32 „kurz, Pause, lang“ nach (`PAD_KURZ_MS`, `PAD_PAUSE_MS`, `PAD_LANG_MS` aus M1). Vor dem langen Teil prüft er VBUS: ist der Pi schon an, kommt kein langer Druck.
*   Kommt nach dem Puls binnen 2 s kein 5 V: `ERR pad_pulse`; ein zweiter Versuch nur nach 10 s und bei VBUS tief.
*   Der Hauptknopf (Arcade, parallel zum Taster, `stueckliste-und-psp.md:45-48`) bleibt unabhängig; der Schalter darf ihn nicht beeinflussen.

### 4.4 Tiefschlaf (H-G9)

*   Wecken per EXT1 auf RTC-GPIOs (0 bis 21), Pegel `ANY_HIGH`, keine Flanke. Folgen als Zeilen in `power_fsm` und Test: (a) PN5180-IRQ **löschen und neu scharf machen** vor dem Schlafen (sonst Dauerschleife, `research.md:207`);
    (b) VBUS in derselben Maske: Schlafen erst nach VBUS 3 s tief, ein Prellen startet den Zähler neu; (c) `rtc_gpio_hold_en` und `gpio_deep_sleep_hold_en` für MOSFET, Weiche, Pad-Schalter, nach dem Wecken Hold lösen **vor** dem ersten Schreiben;
    (d) ROM, Bootloader und Arduino-Start ≈ 250 bis 400 ms [Schätzung], getrennt gemessen (M10).

### 4.5 Änderungen am Leser-Protokoll (Wortlaut)

Stelle: `docs/protocol/reader-v1.md`. **`proto` bleibt 1.** Begründung (Abschnitt 13, Zeilen 573 bis 591; Abschnitt 11, 499 bis 527): Neu sind ein **optionales** Feld am Ende von `HELLO`, neue Zeilentypen vom Leser (alte Dienste ignorieren sie),
neue Fehlercodes und neue Zeilen **vom Box-Dienst**, für die Abschnitt 8 den Rückkanal reserviert hat (Zeilen 289 bis 293). Eine alte Firmware antwortet auf sie mit `ERR code=bad_command` (Zeilen 294 bis 296).
Die Hauptversionen von `fw` und `proto` sind unabhängig. Neue Zeilen dürfen Pflichtfelder haben (der Satz „Neue Pflichtfelder gibt es in Version 1 nicht“, Zeile 581, gilt für **bestehende** Zeilen). `fw` steigt mit Schritt 2 auf 2.0.0.

**Schritt 1:**

| Zeile | Richtung | Felder | Wann |
|---|---|---|---|
| `HELLO` | Leser → Pi | `proto` `fw` `build` `pn5180` **`caps`** (optional, am Ende) | wie bisher. `caps` = Liste durch Komma; Schritt 1 kennt `strom`. Fehlt `caps`: Firmware 1.x |
| `LADER` | Leser → Pi | `in` (`0` oder `1`) | nach dem `HELLO` und bei jeder Änderung von `STROM_IN` (entprellt: hoch 200 ms, weg 1000 ms) |

Der Satz „Alle Felder jeder Zeile sind **Pflicht**“ (Zeile 81) bekommt den Zusatz „außer den als *optional* gekennzeichneten (heute nur `caps`)“.

**Schritt 2:**

| Zeile | Richtung | Felder | Wirkung |
|---|---|---|---|
| `WAKE` | Leser → Pi | `reason` ∈ `tobie` `magnet` `strom` `extern` `reset`; `ring` (`0\|1`: Lauflicht läuft) | einmal direkt nach dem `HELLO`, das auf das erste `PING` nach einem Wecken folgt. `extern` = Pi ohne Zutun des ESP32 eingeschaltet (Knopf) |
| `RING_PI_OK` | Leser → Pi | `an` | Antwort auf `RING_PI` (3.3) |
| `RING_PI` | Pi → Leser | `an` (`0\|1`) | Übergabe des Rings (3.3). Nur, wenn `caps` `weiche` nennt |
| `SLEEP` | Pi → Leser | `hell_ab` `hell_bis` (Sekunden, 3.2) | „Der Pi fährt herunter.“ Ring aus. Keine Antwort (`SLEEP_OK` entfällt: es war nur Diagnose, der Pi fährt ohnehin herunter). Nur bei `caps` `sleep` |
| `CFG` | Pi → Leser | `tobie` (`0\|1`) | darf ein Tobie/Magnet im Schlaf wecken (RTC-Speicher). Wird nach jedem `HELLO` gesendet. Nur bei `caps` `tobie` |

`caps` Schritt 2: `weiche`, `sleep`, `tobie`, `hall`. **Neue Fehlercodes** (Hinweis, ohne `errors` zu erhöhen): `sleep_aborted`, `host_timeout`, `lpcd_noise`, `pad_pulse`. Der Satz „Die Liste ist **vollständig** für Version 1“ (Abschnitt 7) wird entsprechend geändert.
Der Dienst sendet `RING_PI`, `SLEEP`, `CFG` nur, wenn `caps` das Merkmal nennt. **Flashen:** nur über USB; der ESP32 startet neu (`WAKE reason=reset`), schläft während des Flashens nie; `firmware_min` im Update-Paket steigt auf 2.0.0 (Zeilen 586 bis 589).

**Zeitkonstanten, Firmware (`timing.h`):** `LPCD_INTERVAL_MS` 300 [Schätzung, M4], `LPCD_FALSCH_MAX` 3, `PAD_PULS_MS` 150 [Schätzung, M1] (oder `PAD_KURZ_MS`/`PAD_PAUSE_MS`/`PAD_LANG_MS`), `WECK_LAUFLICHT_MAX_S` 30, `VBUS_WEG_ENTPRELL_MS` 3000,
`SLEEP_WARTEN_S` 90, `RING_AUS_VERZ_MS` 1000, `RING_DECKEL_PROZENT` 25, `RING_WECK_HELL` 25, `RING_WECK_GEDIMMT` 5, `STROM_ENTPRELL_HOCH_MS` 200, `STROM_ENTPRELL_WEG_MS` 1000.
**Box-Dienst:** `RING_PI_WDH_S` 5, `RING_AUS_VERZ_S` 2, `STROM_UNBEKANNT_S` 60, `LADER_SPERRE_S` 10 (Schritt 1).
Entfallen gegenüber Rev. 1: `LPCD_ARM_MS`, `LPCD_RUECK_ZYKLEN`, `RING_TIMEOUT_S`, `RING_WECK_SICHER`, `RING_KEEPALIVE_S`, `SLEEP_OK_FRIST_S`.

---

## 5. Hardware-Anforderungen

Nur Anforderungen und Messpunkte; kein Schaltplan. Die Messungen stehen in Abschnitt 10.3 (**M0 zuerst**).

### 5.1 Versorgung des Wächters aus BAT (H-G5, H-G6, P10, R7)

*   BAT (PiSugar-Pad 2) liegt bei 3,0 bis 4,2 V (`research.md:15`). Ein Regler speist ESP32, PN5180-Logik, Hall-Schalter und Teiler **dauernd**. Entweder Buck-Boost auf 3,3 V (TPS63900-Klasse, Ruhestrom nach Datenblatt zu prüfen) oder LDO mit kleinem Ruhestrom (TPS7A02-Klasse) mit bewusstem Dropout. Ruhestrom **mit** 20 µA Last messen, nicht im Leerlauf.
*   Spitzenstrom ≥ 150 mA, ≥ 100 µF niedriger ESR am PN5180 und am Reglerausgang. Belastbarkeit von Pad 2 und Verhalten bei leerem Akku sind nicht dokumentiert (`research.md:217`): M2. Rückfall: eigene Zelle.
*   **Akku leer (P10):** Der Wächter darf bei leerem Akku mit der Unterspannung des Reglers (etwa 3,1 V) ausgehen; den Akku schützt der PiSugar. Danach weckt kein Tobie mehr, bis geladen ist; `tobie=1` ist dann wieder Standard.
*   **SuperMini (R7):** Löten ist in Ordnung. Erst messen (3V3-Pin extern gespeist, nichts an USB, µA im Tiefschlaf); zieht sie zu viel, Power-LED und WS2812 (beide GPIO 48) ablöten oder Brücke trennen; hängt der Platinen-Regler am Netz, auch diesen trennen. Alternative Platine ohne Lade-IC und LED nur, wenn Löten nicht reicht.

### 5.2 Trennung vom USB-5-V des Pi, Rückspeisung (P4; H-G2, H-G12)

*   Der ESP32 hängt nur am BAT-Regler. Das USB-Kabel zum Pi führt Daten und Masse, **nicht VBUS**. Die 5 V des Pi gehen über einen Teiler (**100 kΩ / 150 kΩ**, 10 nF nach Masse: 3,0 V bei 5 V, 3,15 V bei 5,25 V) an `VBUS_SENSE`. Ein Datenkabel ohne VBUS zählt für die Aufzählung (Pull-up an D+ intern, Forenlage); **M7 belegt es.**
*   **Rückspeisung über D+ (P4):** Der Pull-up ist an, sobald der ESP32 läuft, auch wenn der Pi aus ist. M7 misst Strom und Spannung an Pi-D+ und Pi-3,3-V. Fließt Strom in den ausgeschalteten Pi, kommt ein **USB-Schalter** (FSUSB42/TS3USB221-Klasse) in D+/D− dazu; der ESP32 schließt ihn erst, wenn die 5 V des Pi anliegen (`VBUS_SENSE`).
*   Alternative (H-G15 E): normales Kabel mit VBUS lassen. Bleibt Messfall in M7; die eigene Leitung vom Pi-5-V ist sauberer.

### 5.3 PN5180: TVDD (P3, Platine genannt; H-G1)

**Platine:** das blaue Modul „PN5180-NFC R1.1-170710“ (Pins +5V, +3.3V, RST, NSS, MOSI, MISO, SCK, BUSY, GND, GPIO, IRQ, AUX, REQ; Antenne auf der Platine). Laut Community und NXP-Datenblatt (TVDD 2,7 bis 5,5 V, typisch 5 V) speist **+5V die Sendestufe (TVDD)**, +3.3V die Logik (VDD/PVDD);
mit nur 3,3 V an beiden Pins läuft das Modul, aber mit geringerer Reichweite. Ein Elechouse-Modul nennt 4,5 bis 5,5 V für TVDD, eine andere Seite desselben Herstellers 3,3 V für alles: widersprüchlich. [Websuche 10.11.; kein Schaltplan dieser Revision gefunden, **Schaltplan oder Durchmessen der Platine bleibt nötig**: hängt ein Platinen-Regler 5 V → 3,3 V am +3.3V-Pin?]
Die **2,5 cm** stammen nur aus dem Plan (`stueckliste-und-psp.md:200-201`: Chip ≈ 2 cm über dem Sockel, plus Deckel) und sind **nicht gemessen**. Darum ist M0 die erste Messung.

Woher kommen die 5 V für TVDD, wenn der Pi aus ist? Varianten:

| | Variante | Folge für LPCD-Referenz und Aus-Budget |
|---|---|---|
| **B** | TVDD fest 3,3 V: beide Pins am Wächter-Regler | kein Wandler, einfachster Aufbau, kein Mehrverbrauch. Referenz im Schlaf und Betrieb gleich. Reichweite kürzer: M0 entscheidet |
| **A** | kleiner Aufwärtswandler aus BAT auf 5 V (Boost mit Ruhestrom < 5 µA, TPS61xxx-Klasse mit Enable), speist **nur den +5V-Pin**, +3.3V bleibt am Wächter-Regler | volle Reichweite. **Dauernd an:** Referenz stabil, aber Ruhestrom des Wandlers zählt im Aus-Budget (Ziel < 10 µA im Leerlauf; die LPCD-Pulse laden den Ausgangskondensator, mit 300 ms Takt Mittel eher einige 10 µA, M3). **Vom ESP32 geschaltet** (Enable nur für den LPCD-Puls und den Betrieb): Aus-Budget fast null, aber der Wandler braucht beim Einschalten Anlaufzeit (≈ 1 ms bis stabil) und die Referenz hängt von der Anlaufspannung ab; vor jedem LPCD-Abgleich und jeder Messung mit **derselben** Schaltfolge fahren |
| **C** | +5V-Pin aus Pi-5-V im Betrieb, Wandler nur im Schlaf | **verworfen:** LPCD-Referenz springt zwischen Schlaf und Betrieb (H-G1b) |

*   Beim Aus-Budget fallen auch bei Variante A nur wenige Mikroampere an: 10 bis 50 µA × 3,7 V × 16 h ≈ 0,001 bis 0,003 Wh am Tag, gegen 0,08 bis 0,15 Wh für Wächter und PiSugar (Abschnitt 7). Das Budget entscheidet die Wandlerwahl nicht; die Reichweite entscheidet.
*   **Entscheidungsregel (Tobias, Nachtrag):** Reicht 3,3 V **mit Reserve** für Deckel + Chiphöhe (M0), **entfällt der 5-V-Wandler im Zustand Aus** (Variante B). Sonst kommt er (Variante A). Vorrang hat die Reichweite. Bis M0 vorliegt, beschreibt der Entwurf beide Varianten; der Pinplan (5.6) braucht für A einen Enable-Pin: GPIO 5 (statt des optionalen ADC).
*   Für alle Varianten: LPCD vor jedem Einschlafen neu abgleichen (4.2); keine zwei Regler parallel an derselben Schiene; Pufferkondensator ≥ 100 µF am PN5180. Schritt 2 hängt für LPCD an M0, M4 und der Wahl A/B.

### 5.4 Pad-10-Schalter (H-G7)

*   **PhotoMOS-Relais** (TLP175A/AQY-Klasse, Sperrstrom < 1 µA): Kontakt zwischen BAT und Pad 10 wie der Taster, Vorwiderstand am GPIO, 100 kΩ nach Masse an der LED-Seite, Seite im Tiefschlaf auf **Low gehalten**. Ein Bauteil, zwei Widerstände. Erst M1 (Pegel, Pull-Widerstand, Zeit), dann die Bauteilwahl bestätigen.

### 5.5 Ring-Schalter (H-G8)

*   **Lastschalter-IC** (TPS22918-Klasse): 3,3-V-Enable, Slew-Rate-Begrenzung, Ausgangsentladung, Sperrstrom < 1 µA; ein Teil statt vier. Hinter dem PTC 1,1 A (`stueckliste-und-psp.md:67-70`). Ringstrom bei offenem Schalter < 10 µA (M8).
*   Reihenfolge beim Einschalten: erst Schalter, nach 5 ms Daten. Bei Verlust der 5 V: beide Leitungen sofort auf neutral (3.3 Nr. 7). Der Dauerstrom ≥ 1 A ist wegen des Deckels nur ein Fehlerfall (Vollweiß 2,4 A, `stueckliste-und-psp.md:67-69`).

### 5.6 Hall-Schalter, `STROM_IN`, Pinplan (R6, P1, P11; H-G11)

*   **Hall-Schalter** (DRV5032-Klasse, < 1 µA) im Deckel, zweite Weckquelle für Tonies (Magnet im Fuß, `stueckliste-und-psp.md` Punkt 10; am Muster zu prüfen). Der Lautsprechermagnet ist ein konstantes Feld und muss weg vom Sensor. Karten ohne Magnet wecken nur über LPCD. M6.
*   **`STROM_IN`:** Teiler (100 kΩ / 150 kΩ) von der USB-C-Eingangsspannung an einen RTC-Pin. Der Hauptknopf wird in Schritt 2 nicht mitgelesen; für später (P7) wird nur ein Teiler an Pad 10 vorgesehen.
*   **Pinplan.** GPIO 8 bis 13 bleiben wie in `config.example.h:9-14` (RST 8, BUSY 9, NSS 10, MOSI 11, SCK 12, MISO 13; GPIO 10 bis 13 sind die FSPI-Pins). Gemieden: GPIO 0, 3, 45, 46 (Strapping; GPIO 3 bleibt offen), 19/20 (USB), 43/44 (UART0), 48 (LED/WS2812 der SuperMini).
    Wecken aus dem Tiefschlaf nur über RTC-Pins (GPIO 0 bis 21); gehaltene Ausgänge ebenfalls.

    | Funktion | GPIO | Art |
    |---|---|---|
    | PN5180-IRQ (**neuer Draht**, `config.example.h` hat keinen) | 14 | Weck-Eingang |
    | `STROM_IN` | 15 | Weck-Eingang |
    | Hall-Schalter | 16 | Weck-Eingang |
    | `VBUS_SENSE` | 17 | Weck-Eingang |
    | Pad-10-Schalter | 18 | Ausgang, gehalten |
    | Ring-MOSFET | 21 | Ausgang, gehalten |
    | Weiche `RING_SEL` / Freigabe | 4 | Ausgang, gehalten (siebter Pin: P11 nennt nur 14–18 und 21, `VBUS_SENSE` fehlt dort; GPIO 4 ist RTC-fähig, kein Strapping) |
    | Ring Daten / Takt (zweiter SPI-Host, Matrix) | 1 / 2 | Ausgang; im Schlaf neutral durch die Weiche |
    | Enable 5-V-Wandler (nur Variante A, 5.3) oder Akku-ADC (optional, H8) | 5 | Ausgang, gehalten / ADC1 |

    **Welche Pads die eigene SuperMini wirklich herausführt, wird am Exemplar gezählt** (die Produktseite ist kein Schaltplan); fehlen Pins, entfallen zuerst ADC und der Hall-Schalter. Pi-Seite: GPIO 23/24 bleiben am Ring (Weiche), die Pi-Belegung ändert sich nicht.

---

## 6. Schneller Start, Frühton, Töne

### 6.1 Ziele (Messziele, P9)

| Messpunkt | Ziel | Grundlage |
|---|---|---|
| Auslöser → Lauflicht | **unter 1,5 s, so schnell wie die Messung erlaubt** | Tobie: LPCD/Hall ≤ 0,3 s + Aufwachen ≈ 0,3 s + Lesung + Puls + 5 V am Ring ≈ 0,95 s [Schätzung]. Knopf und Strom: ESP32 muss erst booten (H-G9d). Getrennt messen (M10) |
| 5 V am Pi → Frühton | ≤ 5 s | Firmware 1,25 s + Kernel ≈ 2 s + Frühdienst ≈ 1,5 s [Schätzung] |
| 5 V am Pi → `Bereit` | ≤ 8,5 s | Maßnahmen 6.4 |
| Auflegen (Aus) → Hörspiel | **≤ 10 s** (Brief), Rückfall 15 s (E13) | 1,0 + 8,5 + 0,5; ehrgeizig |
| Auflegen (Bereit) → Hörspiel | ≤ 3 s | Dauerabfrage wie heute, `box-software.md:1043-1058` (0,94 s) |

Belegt sind nur Fremdwerte: Pi 3 mit getrimmtem Buster 1,79 s Kernel + 5,78 s Userspace, Firmware 1,25 s (`research.md:145, 150`); für den Pi 3A+ mit Pi OS Lite gibt es keine Messung (`research.md:139`).

### 6.2 Frühton: ein Ton, nicht zwei (P6; G7, G8)

*   **Dienst:** `tobibox-fruehton.service` (`deploy/pi/`), **`Type=simple`, kein `Before=tobiboxd.service`**. Er blockiert den Box-Dienst nie. `After=sound.target`, `DefaultDependencies=no`. Er spielt `box/sounds/start.wav` über das `softvol`-Gerät (Entscheidung J5, `box-software.md:446`), Pegel wie `hinweis`.
*   **Entscheidung, ob er spielt:** nur im Modus `normal` bei sicherer Uhr (E14). Die Uhr-Regel (`zeit_ok` aus RTC, `power.py:34, :252-256`) wird in ein kleines gemeinsames Modul ohne Asyncio gezogen, das `power` und der Frühdienst laden. Die Leise-Zeiten liest er aus `config.json` über `quiet.wirkung_jetzt` (`quiet.py:104`).
    Dauert der Python-Start auf dem Pi 3A+ zu lange (M-P2), entfällt der Frühdienst, und der Box-Dienst spielt `start` wie heute (kein Rückfall mit vorberechneter Datei: der Dienst kennt beim Beenden den nächsten Start nicht, G7).
*   **Marke und feste Reihenfolge:** `/run/tobibox/fruehton` (tmpfs, gelöscht bei jedem Einschalten) enthält `start` (Ton läuft) oder `keiner` (bewusst unterlassen), nach dem Spielen `fertig`. Der Frühdienst schreibt sie **zuerst**, startet den Ton und endet; die Marke sagt „entschieden“, nicht „fertig gespielt“.
    `app` liest sie beim Start einmal und löscht sie: war sie da, ist `Bereit(fruehton=True)` und `session._bereit` (`session.py:844-845`) spielt **keinen** `start`. Steht sie noch auf `start`, wartet `app` mit **jedem** Ton des Kerns bis `fertig`, höchstens `FRUEHTON_WARTEN_S` = 3 s. So überlagern sich Frühton und `hinweis` nicht. Keine `boot_id` in der Marke (tmpfs und Löschen reichen, G8).
*   **Dienst-Neustart:** keine Marke da, also spielt der Kern `start` wie heute (P5, Z10). Der Boot-ID-Mechanismus für den Tobie (`lauf.py`) bleibt.

### 6.3 Lader-Ton (R4) und der Doppel-Ton-Fall (G14, P6)

Der Kern (`core.py`) spielt `lader` über `TonSpielen`; Regel 2a: `lader` entfällt unter „leiser“, „stumm“, bei unsicherer Uhr und im Lernmodus; er wird nicht durch `hinweis` ersetzt (anders als die Töne in `_TOENE_UNTER_STUMM`, `core.py:44`, `:119`).
Während ein Hörspiel spielt, gilt S9: nur Ring. Töne zugleich gibt es nicht (Entscheidung L, `core-interface.md:316`).

**Auslösung in `idle`:** `lader` und Rückmeldung nur bei einem Wechsel „kein Strom“ nach „Strom“ **nach der ersten bekannten Messung** des laufenden Dienstes. Die erste bekannte Messung (auch `None` → `True` spät nach dem Start) löst nur den Sync-Check aus, nie Ton oder Ring.
Die Sperre `LADER_SPERRE_S` = 10 s beginnt bei `Bereit` und mit jeder Rückmeldung.

| Fall | `start` | `lader` | Warum kein Doppel-Ton |
|---|---|---|---|
| Aus, Strom kommt (Z03) | Frühton | nein | erste Messung (`LADER`-Zeile oder `pisugar-server`) ist `True`, auch wenn sie spät kommt |
| Aus, Hauptknopf am Sockel | Frühton | nein | erste Messung |
| Bereit, Strom kommt später | schon gespielt | ja | Wechsel nach der ersten Messung und nach der Sperre ab `Bereit` |
| Strom kommt in den ersten 10 s nach `Bereit` | Kern- oder Frühton läuft | nein (Ring ja) | Sperre ab `Bereit`; Frühton ≤ 5 s liegt vor `Bereit` |
| Dienst-Neustart am Sockel | Kern spielt `start` | nein | erste Messung, kein Wecken |
| Spielt | – | nein | S9 |
| Wackelkontakt | – | einmal je 10 s | Sperre |
| Frühton läuft noch, Kern will `hinweis` | – | – | Wartereihenfolge 6.2 |

### 6.4 Boot-Kürzung (Arbeitspaket, Pi; Reihenfolge: messen, einzeln ändern, neu messen)

`systemd-analyze blame` und `critical-chain`, dazu Stoppuhr per ESP32 (Lauflicht bis Ton). Maßnahmen, jede mit Beleg oder als Versuch markiert: `cloud-init` abschalten (P33, `research.md:157`); `NetworkManager-wait-online` maskieren, `Bereit` hängt nur an MPD (`app.py:919-927`);
Bluetooth/`hciuart` aus (P20, P31); unnötige Dienste und Timer aus (`man-db`, `apt-daily*`, `avahi`, `rsyslog`, `dphys-swapfile`, `ModemManager`, `exim4`; P20/P21); `tobiboxd` und MPD parallel, `.pyc` vorkompiliert, schwere Importe verzögern (`python -X importtime`);
Versuche ohne Beleg: `quiet`/`loglevel=3`, `gpu_mem=16`, SD-Karte A1/A2 mit `noatime` (`research.md:159`). Abbruch: Nach den belegten Maßnahmen keine 8,5 s bis `Bereit` ⇒ E13 (15 s). Kein Eigenbau-Image.

---

## 7. Budget ohne Sockel, typischer Tag [Schätzung]

Grundlage: 15 Wh nutzbar (`stueckliste-und-psp.md:335-338`); 4 h Hören, 10 Pausen, der Rest Aus, jede Nacht am Sockel.

| Posten | Rechnung | Wh |
|---|---|---|
| Hören | 4 h × 1,6 bis 1,9 W | 6,4 bis 7,6 |
| 10 Pausen je 10 min Bereit (Dauerabfrage, R2) | 100 min × 1,0 bis 1,3 W | 1,7 bis 2,2 |
| 3 Starts aus Aus | 3 × 25 s × 1,5 W | 0,03 |
| Aus (16 h): PiSugar ≤ 1 mA + Wächter 0,3 bis 1,5 mA | 1,3 bis 2,5 mA × 3,7 V × 16 h | 0,08 bis 0,15 |
| **Summe** | | **8,2 bis 10,0** |

*   Reserve 5,0 bis 6,8 Wh (≈ 3 bis 4 h Hören). Schlechtester Fall Bereit bei 1,75 W: bis 10,7 Wh. Die Wächter-Zahl ist gegenüber Rev. 1 höher (LPCD bei 300 ms: realistisch 0,4 bis 1,5 mA, H-G10); sie ändert die Summe kaum, das Budget hängt an Hören und Bereit.
*   Die Last des Wächters liegt auf BAT statt auf der 5-V-Seite (Teil der 0,2 bis 0,35 W, `research.md:88`): die Spalte „Bereit“ ist eher zu hoch; M3/M-B4 messen es.
*   **Wozu die Frist:** Bereit den ganzen Tag (16 h × 1,0 bis 1,3 W) leert den Akku. 10 min kosten 0,17 bis 0,22 Wh, ein Kaltstart 0,01 Wh (`research.md:120`): die Frist ist Komfort, nicht Energie.
*   LPCD in Bereit würde nur 0,075 Wh am Tag sparen (R2); Light-Sleep des ESP32 bleibt eine spätere Frage.

---

## 8. Folgen für Verträge und Design (P8, P12)

### 8.1 Verträge in zwei Schritten

Zeilenangaben: Stand des Repos am 10.11. „Klar.“ = Klarstellung, „inh.“ = inhaltlich.

**Schritt 1: sofort nach Freigabe (19 Stellen: 14 inh., 5 Klar.)**

| # | Datei | Abschnitt (Zeile) | Art | Änderung |
|---|---|---|---|---|
| A1 | `reader-v1.md` | 3 Zeilentabelle (72-109) | inh. | `LADER`, `HELLO.caps` |
| A2 | `reader-v1.md` | 3 „Alle Felder … Pflicht“ (81) | Klar. | optionales Feld `caps` |
| A3 | `reader-v1.md` | 12 Verbindungsaufbau (529-551) | inh. | nach `HELLO` kommt `LADER` |
| A4 | `reader-v1.md` | 13 Versionsregel (573-591) | Klar. | neue Zeilen mit Pflichtfeldern erlaubt; `fw`/`proto` unabhängig; Befehle vom Dienst nur bei passendem `caps` |
| A5 | `reader-v1-examples.txt` | neue Abschnitte | inh. | `HELLO caps=strom`, `LADER` (gültig, ungültig) |
| A6 | `core-interface.md` | 3.1 `LeserHallo` (128) | inh. | `caps: str = ""` |
| A7 | `core-interface.md` | 3.3 `Bereit` (194) | inh. | `fruehton: bool = False` |
| A8 | `core-interface.md` | 3.6 `LaderGeaendert` (227) | inh. | Bedeutung „Strom, jede Quelle“; `quelle: "pisugar"\|"leser"`; Vorrang Leser |
| A9 | `core-interface.md` | 3.6 `SyncAbgebrochen` (234) | Klar. | keine Wiederholung am Lader |
| A10 | `core-interface.md` | 4 `TonSpielen` (316) | inh. | Ton `lader` |
| A11 | `core-interface.md` | 5.2 Zeile `idle.py` (359) | inh. | Ausgang `lader`; Frist nur ohne Strom |
| A12 | `core-interface.md` | 6.2 Konfliktregeln (468-470) | inh. | Regel 2a für `lader` (6.3) |
| A13 | `core-interface.md` | 8.1 Töne (851-858) | inh. | Pegel von `lader` und Frühton wie `hinweis` |
| A14 | `core-interface.md` | 9 Punkt 9 Leerlauf (1123-1152) | inh. | 10 min ohne Strom; Andocken; erste Messung; 60 s unbekannt; Wiederholung entfällt |
| A15 | `core-interface.md` | 11 Konstanten (1344-1353) | inh. | `LEERLAUF_S` 600; `START_WIEDERHOLUNG*` entfallen; neu `LADER_SPERRE_S`, `STROM_UNBEKANNT_S`, `FRUEHTON_WARTEN_S` |
| A16 | `mqtt-v1.md` | 3.3 `lader` (156), 6.2 (601) | Klar. | „Strom am Eingang, jede Quelle“ |
| A17 | `ha-websocket-v1.md` | `tobibox/box/sync` (940-950) | Klar. | „Lader“ = jede Quelle |
| A18 | `data-model.md` | 1.6 Dateien (134, 150-154) | inh. | flüchtige Datei `/run/tobibox/fruehton` (Text `start`/`keiner`/`fertig`) |
| A19 | `data-model.md` | 2 `hinweis_pegel` (208), Töne | inh. | `lader.wav`, Pegel; Pegel des Frühtons |

**Schritt 2: nach den Messungen (15 Stellen: 13 inh., 2 Klar.)**

| # | Datei | Abschnitt | Art | Änderung | Freigabe durch |
|---|---|---|---|---|---|
| B1 | `reader-v1.md` | 3 Zeilentabelle | inh. | `WAKE`, `RING_PI_OK` | M1, M2, M7 |
| B2 | `reader-v1.md` | 3 `caps`-Werte | Klar. | `weiche`, `sleep`, `tobie`, `hall` | M4, M6, M8 |
| B3 | `reader-v1.md` | 7 Fehlercodes (231-252) | inh. | vier Codes; Satz „Liste vollständig“ | M1, M7 |
| B4 | `reader-v1.md` | 8 Zeilen zum Leser (281-297) | inh. | `RING_PI`, `SLEEP`, `CFG` | M1, M8 |
| B5 | `reader-v1.md` | 10 Zeitkonstanten (460-497) | inh. | Konstanten aus 4.5 | M1, M4, M10 |
| B6 | `reader-v1.md` | 12 Verbindungsaufbau | inh. | `CFG`, `RING_PI`, `WAKE` nach dem `HELLO` | M1, M8 |
| B7 | `reader-v1.md` | 13 (586-589) | inh. | `firmware_min` 2.0.0; Weg zum Flashen | M7 |
| B8 | `reader-v1.md` | Festlegungen (593-666) | inh. | `WAKE` einmal je Wecken; `SLEEP` einziger Schlaf-Auslöser; Übergabe; Deckel 25 % in der Firmware | M8 |
| B9 | `reader-v1-examples.txt` | neue Abschnitte | inh. | Beispielzeilen (Testgrundlage der Firmware) | alle oben |
| B10 | `core-interface.md` | 3.1 neues Ereignis | inh. | `LeserWecken(grund, ring)` | M1 |
| B11 | `core-interface.md` | 4 Befehle | inh. | `RingUebergeben`, `LeserSchlafen`, `LeserKonfigurieren`; Empfänger, Rang in `_RANG` (`core.py`), Reihenfolge gegenüber `HerunterfahrenAngefordert` | M8 |
| B12 | `core-interface.md` | 6.5 und 10 (643, 1296-1320) | Klar. | `app`: `SLEEP` vor `poweroff`, `RING_PI`; `led` gibt den Ring-Wunsch an `app` | M8 |
| B13 | `core-interface.md` | 11 Konstanten | inh. | `RING_PI_WDH_S`, `RING_AUS_VERZ_S` | M8 |
| B14 | `core-interface.md` | Konfiguration `[leser]` (Ort beim Einarbeiten klären: heute kein `[leser]`-Treffer in den Verträgen) | inh. | Schlüssel `tobie_wecken` | M4 |
| B15 | `mqtt-v1.md` | 3.4 `fehler` (220) | inh. | `baustein="leser"`, `code="schlafen_abgebrochen"` | M1 |

Nicht mehr nötig gegenüber Rev. 1: `RING`-Muster, `SLEEP_OK`, `CFG wach`, `HB`-Sonderfall zu `polls` (kein Wachbetrieb), `wring`, `quiet`-Fensterfunktion im Vertrag, Konstanten `LPCD_ARM_MS` und weitere. **Gesamt 34 Stellen** (Rev. 1: 26, unvollständig gezählt: P12).

### 8.2 Was aus S1 bis S11 und „Start am Lader“ gilt

| Eintrag | Schicksal |
|---|---|
| R8 Andocken weckt, R10 eine Buchse | gelten (Z03; Messung M13 prüft `battery_power_plugged`) |
| S1, S7, S8, S10 | gelten (Sync: `syncregel.py` unverändert; einmal je Andocken, Sperre 10 s; Sockel und Kabel nicht unterscheidbar) |
| S2, S3 Kurz-Modus, Wiederholung des Start-Syncs, Schleifenbremse, `Bereit.einschalten`, „erste Messung vor Bereit“, S6 Update vormerken | **entfallen** (am Sockel immer bereit; `fruehton` ersetzt `einschalten`). Im Code: `idle.py:41, 61-65, 168-175, 199-210, 281` entfernen |
| S4 liegender Tobie spielt beim Start | gilt (CUJ 20); nachts schützt „stumm“ |
| S5 Leise-Zeiten | gilt: Frühton, `lader` nur im Modus „normal“ bei sicherer Uhr; Akku-Anzeige 15/5/3 %, Stufe ≥ 1 (`led.py:114`: 3 % ergibt heute Stufe 0), Ausnahme vom Faktor 0,4 (`led.py:64`) |
| S9 spielendes Hörspiel: nur Ring | gilt |
| S11 Frühstart-Ring | erledigt durch das Lauflicht des ESP32 und die Weiche |
| Entscheidung G, `lauf.json` | gilt unverändert |

### 8.3 Design, Plan, Betrieb, Code (kurz)

*   `box-software.md`: CUJ 10, 15, 16, 18, 20 und neue 21 bis 25; Entscheidung O, B2; Baustein 1 und 2; Tabelle „Strom / Leerlauf“ (1380-1397) mit den Zeilen aus 1.2; Risiken; AP 4.1, 4.3; neue Arbeitspakete.
*   `stueckliste-und-psp.md`: 1.5 Laufzeit, Teil 2 Pinbelegung (389-421), Stückliste (Regler, PhotoMOS, Lastschalter, Weiche, Hall, USB-Schalter), 5.5.1 (Ring bleibt am Pi, Weiche), 8.2.4.
*   `docs/betrieb/pisugar-wecker.md` Abschnitt 4 und 6; `mac-prototyp.md:1730` (Probe „Start-Sync am Lader und Wiederholung“); `docs/timing.md` (Aus → Hörspiel); `firmware/tobibox-reader/README.md` und `config.example.h` (Pins).
*   Code: `idle.py`, `led.py` (Helligkeit, Entprellen, Bereit dunkel, Ausgabe), `reader.py`, `app.py`, `power.py` (kein `set_anti_mistouch` mehr), `session.py:844-845`, `core.py:44, 119`, neu `fruehton.py` und das gemeinsame Uhr-Modul, `deploy/pi/`.

---

## 9. Offene Punkte

**Für Tobias (nicht entschieden):**

| # | Frage | Vorschlag |
|---|---|---|
| P3 | TVDD-Quelle im Aus (Platine bekannt: PN5180-NFC R1.1-170710) | nach M0: reicht 3,3 V mit Reserve, entfällt der Wandler (B); sonst A (5.3) |
| E3 | Akku am Sockel dauernd bei 100 %? | M9 prüft eine Ladegrenze; sonst hinnehmen |
| E4 | Hauptknopf lang am Sockel startet die Box wegen `STROM_IN` sofort neu (Z04) | hinnehmen: am Sockel ist „bereit“ gewollt. Kein Zyklus, da der Pi am Sockel nur nach Hauptknopf lang herunterfährt |
| E9 | Frist ab Abziehen oder ab dem letzten Spielen? | ab Abziehen (sonst Aus beim Hochnehmen nach einer Nacht) |
| E10 | Pi startet, kommt nicht hoch: ESP32 schaltet nach 120 s den PiSugar aus und sperrt Tobie-Wecken? | ja, einmal je Wecken (Langdruck-Pfad); sonst nur Ring aus und HA-Hinweis |
| E13 | Ziel 10 s, Rückfall 15 s? | ja, Entscheidung nach M-P1 |
| E14 | Frühton nur im Modus „normal“? | ja |

**Technisch offen (Messung oder Annahme):** Hall weckt ohne Lesung (Fehlweckung durch fremde Magnete, M6); 10 % Sicherheitsrand für die RTC (M15); Vorrang des Leser-Werts bei Widerspruch zu `pisugar-server` (Vorschlag); Hauptknopf-Weg am Pi (P7, M12);
SuperMini-Pads 14 bis 18/21 am Exemplar zählen; Wahl des Weiche-Chips; „Pi hängt bei 5 V“ erkennt der ESP32 nicht (Annahme wie heute); Zwischen-Wecken (Kurzwach) beim Hall-Bezug.

---

## 10. Arbeitspakete

Neue Nummern **E1-x** (Schritt 1) und **E2-x** (Schritt 2), Nachtrag zum Umsetzungsplan (`box-software.md` ab 1955). Modelle nach `CLAUDE.md`: Haiku für Doku und Boilerplate, Sonnet für Logik, Firmware, Tests mit Bezug zur Hardware.

### 10.1 Schritt 1: am Mac und in der Simulation (nach Freigabe durch Tobias)

| AP | Modell | Inhalt | Abhängig von |
|---|---|---|---|
| **E1-0** | Sonnet | Verträge A1 bis A19 einarbeiten; Gegenlesen durch einen Goldfisch | Freigabe |
| **E1-1** | Sonnet | `idle.py` + `test_idle.py`: Frist 600 s nur ohne Strom; Strom verwirft, Abziehen beginnt neu; zwei Strom-Quellen mit Vorrang Leser; `None` 60 s; erste Messung ohne Rückmeldung; Sperre ab `Bereit`; Wiederholung und `start_wdh` entfernen | E1-0 |
| **E1-2** | Sonnet | `core.py` Regel 2a, `events.py` Ton `lader`, `session.py:844-845` + `Bereit.fruehton`, `app.py` (Marke lesen, Ton-Wartereihenfolge), Konfiguration | E1-0 |
| **E1-3** | Haiku | Ton `lader.wav` (`tools/make_sounds.py`, −18 LUFS, `lautheit.json`), `sounds.pegel` | E1-0 |
| **E1-4** | Sonnet | `led.py`: Akku-Anzeige 15/5/3 %, Stufe ≥ 1 (`led.py:114`), Ausnahme vom Faktor 0,4, Entprellen, 5 % während Gute Nacht; `test_led.py` | E1-0 |
| **E1-5** | Sonnet | gemeinsames Uhr-Modul (`power.py:252-256`), `fruehton.py`, `deploy/pi/tobibox-fruehton.service`, Test mit simulierter Uhr | E1-0 |
| **E1-6** | Sonnet | `reader.py` (`LADER`, `caps`, `LaderGeaendert(quelle="leser")`), Sim-Leser sendet `LADER`; Beispiele in `reader-v1-examples.txt` | E1-0 |
| **E1-7** | Sonnet | CUJ-Tests 16, 23, 24, 25 und die Fälle der Tabelle 6.3 (Doppel-Ton, Wackelkontakt, `pisugar-server` hängt, Strom kommt beim Herunterfahren), simulierte Uhr | E1-1 bis E1-6 |
| **E1-8** | Haiku | Doku nachziehen (8.3); Messskript Bootzeit und Prüfliste zu 10.3 | E1-7 |

### 10.2 Schritt 2: nach den Messungen

| AP | Modell | Inhalt | Abhängig von |
|---|---|---|---|
| **E2-0** | Sonnet | Verträge B1 bis B15 einarbeiten; Gegenlesen | Tor T1 (unten) |
| **E2-1** | Sonnet | Firmware-Logik nativ (`pio test -e native`): `power_fsm` (4.1 bis 4.4 inkl. Bezug, Pad-Regeln, Tests zu G1, G4, Prellen, `sleep_aborted`), Lauflicht-Engine, `protocol.cpp`; zusätzlich als Host-Programm mit Zeilen auf stdin/stdout (G12) | E2-0 |
| **E2-2** | Sonnet | `reader.py`/`app.py`/`led.py`: `WAKE`, `SLEEP`, `CFG`, `RING_PI`, Bereit dunkel und Aufleuchten, Ring-Wunsch; Sim-Leser spricht das Host-Programm über eine Pipe an | E2-0, E2-1 |
| **E2-3** | Tobias, Sonnet | Hardware-Firmware: `hw_power.cpp`, `hw_ring.cpp` (zweiter SPI-Host), Pins nach 5.6; PN5180-Firmware-Update-Werkzeug; Flashen mit `WAKE reason=reset` | E2-1 |
| **E2-4** | Sonnet | CUJ-Tests 21, 22 und 24 (Tobie während des Herunterfahrens), `host_timeout`, `OHNE_HOST` | E2-2 |
| **E2-5** | Tobias | Gesamtprobelauf: Tagesverlauf, Powerbank, Auto, Nacht (Ring-Helligkeit), Akku-Budget | alles |

### 10.3 Messliste am Breadboard und Muster (Ja/Nein-Kriterien, geben Schritt 2 frei)

Tobias misst, Sonnet liefert Messfirmware (`lpcd_probe`). Jede Zeile gibt die genannten Vertragsstellen frei; **Tor T1:** M1, M2, M7, M8 = Ja (oder der Rückfall steht), dann werden B1 bis B15 eingefroren. Die Tobie-Weckwege hängen an M0, M4 und M6; M0 kommt vor allen anderen.

| # | Messung | **Ja** (gibt frei), wenn … | Nein bedeutet |
|---|---|---|---|
| M0 | **Erste Messung, Reichweite am Testaufbau (Tobias):** Tonie und NTAG-Karte langsam von oben über die Antenne senken, Höhe über der Platine notieren, ab der zuverlässig erkannt wird (10 von 10 Versuchen). Je einmal mit 5 V am +5V-Pin (3,3 V am +3.3V-Pin) und einmal mit 3,3 V an beiden Pins | 3,3 V reicht mit Reserve (mind. 5 mm) über Deckel + Chiphöhe (Plan: ≈ 2,5 cm, nicht gemessen) ⇒ Variante B, kein Wandler im Aus | Variante A (Wandler); dann zusätzlich Ruhestrom des Wandlers in M3 |
| M1 | Pad 10: Pegel, Strom, Pull-Widerstand; Zeit Puls → 5 V; kürzester wirksamer Puls; Anti-Mistouch ab Werk | ein Puls von höchstens 500 ms (oder „kurz, Pause, lang“ mit Zeiten) schaltet den ausgeschalteten PiSugar 20 von 20 ein, und die Zeit Puls → 5 V ist gemessen | ESP32 kann nicht wecken: nur Knopf und Strom (Strom nur über PiSugar-Eigenschaft); Konzept ohne E2-3 |
| M2 | Pad 2 (BAT): Last 150 mA Spitze, 100 µF, Verhalten bei leerem Akku | Spannung bleibt über 3,0 V, Ladestandsanzeige und Tiefstand-Schutz des PiSugar unverändert | eigene Zelle oder kein Wächter in Aus |
| M3 | Ruhestrom Aus mit µA-Messgerät, über 1 h Mittel, auch kalt; SuperMini vor/nach Ablöten (R7); bei Variante A mit Wandler dauernd an und geschaltet, mit LPCD-Takt | Summe PiSugar + Wächter ≤ 3 mA | Budget (Abschnitt 7) neu rechnen |
| M4 | LPCD durch den Deckel mit der nach M0 gewählten TVDD-Variante (Referenz im Schlaf, Abgleich bei Spannungsschwankung des Akkus 4,2 bis 3,4 V): Tonie (SLIX2) und NTAG, PN5180-Firmware ≥ 4.0, Abheben meldet, 24 h im Gehäuse | 10 von 10 Auflegen erkannt, ≤ 3 Fehlweckungen je Tag | Karten wecken nur per Hauptknopf; Tonies über Hall (M6) |
| M6 | Hall-Schalter durch den Deckel mit Tonie-Fuß; Lautsprechermagnet; fremde Magnete | Tonie 10 von 10, Lautsprecher löst nie aus, Ruhestrom < 5 µA | Tonies wecken nur über LPCD (M4) oder Hauptknopf |
| M7 | USB ohne VBUS-Ader: Enumeration; Strom und Spannung an Pi-D+ und Pi-3,3-V bei Pi aus, ESP32 wach | Pi sieht den ESP32, und in den Pi fließen < 10 µA (Pi-3,3-V-Schiene < 0,3 V) | USB-Schalter (P4) in die Stückliste; Enumeration nein: Ideal-Diode-Rückfall (Plan) |
| M8 | Ring: zweiter SPI-Host neben PN5180; Weiche ESP32 → Pi und → neutral; Ringstrom bei offenem Schalter | 60 min ohne Flackern oder Lesefehler; Umschalten ohne sichtbares Flackern über ein Bild; neutral = Ring dunkel; Ringstrom < 10 µA | Weiche umbauen; sonst R1 neu mit Tobias |
| M9 | „Einschalten bei Strom“ (Flanke/Pegel), Ladegrenze (E3, E4) | beantwortet E4/E3 | kein Tor |
| M10 | Zeiten getrennt: Auslöser → ESP32 wach, → 5 V am Ring, → Lauflicht (Tobie, Hall, Knopf, Strom) | Mittel unter 1,5 s | Ziel mit Tobias anpassen (P9), kein Tor |
| M11 | Einbruch der 5-V-Schiene beim Pi-Start mit Lauflicht, kalt, bei 20 % Akku | Schiene ≥ 4,75 V (Brownout Pi 4,63 V) | Lauflicht dunkler oder erst nach dem Pi-Start |
| M12 | Hauptknopf am Pi (P7): kommt `Hauptknopf(lang)` im Dienst an? (`taste_befehl` oder `pin_haupt`, `core-interface.md:221`) | ja, Zeiger wird gesichert und `SLEEP` gesendet | Mitlesen durch den ESP32 (Teiler an Pad 10), bis dahin Hauptknopf lang ohne `SLEEP` |
| M13 | `battery_power_plugged` an der einzigen Buchse; schwache 1-A-Quelle; Powerbank/Auto weckt wiederholt (Sperre) | Wert stimmt, Akku sinkt nicht trotz „Strom“ | Tiefstand am Sockel neu |
| M14 | Sichtbarkeit von 5 % und 25 % durch das Gehäuse; nachts nicht blendend | Tobias bestätigt beide Werte | Werte anpassen |
| M15 | RTC-Genauigkeit des ESP32 über 12 h | Abweichung ≤ 10 % | Sicherheitsrand größer |
| M-P1 | Pi 3A+: Bootzeit 5 V → Frühton, `Bereit`, Hörspiel, vor/nach jeder Maßnahme 6.4 | `Bereit` ≤ 8,5 s | E13: Ziel 15 s |
| M-P2 | Frühdienst: Python-Startzeit, ALSA gleichzeitig mit MPD (`softvol`) | Ton ≤ 5 s nach 5 V | Frühdienst entfällt (6.2) |

---

## 11. Befunde der Goldfische: was daraus wurde

| Befund | Stand | Wo / warum |
|---|---|---|
| G1 Wecken bei liegendem Tobie | eingearbeitet | 4.2, CUJ 22, Z01 (R3) |
| G2 Am Sockel nie aus | eingearbeitet | 1.2 (Quellen, 60 s), Z04, 4.2 Strom, CUJ 23 (P1); Wirkung von „Einschalten bei Strom“ bleibt M9 |
| G3 LPCD in Bereit | durch Resolve entfallen | R2 |
| G4 Tobie während des Abschaltens | eingearbeitet | 4.1 `ABSCHALTEN`, 4.2, CUJ 24 |
| G5 Aufteilung des Rings | durch Resolve entfallen | R1 (Hardware-Weiche statt Muster-Engine) |
| G6 `RING`-Regeln, `dur`, Gleichheitstest | durch Resolve entfallen | R1 (kein Muster-Protokoll); Deckel in der Firmware nur für das Lauflicht (3.1) |
| G7 Frühdienst | eingearbeitet | 6.2 (kein `Before=`, gemeinsame Uhr-Regel, kein vorberechneter Rückfall, Überlappung, M-P2) |
| G8 „Nie zwei Töne“, Z10 | eingearbeitet | Z10, 6.2, 6.3 (erste Messung, Sperre ab `Bereit`, keine `boot_id`) |
| G9 `wring`/`wring_s` | eingearbeitet in geänderter Form | R5, 3.2: `hell_ab`/`hell_bis` mit Sicherheitsrand, gedimmt statt aus; Uhr im ESP32 bleibt, M15 prüft sie |
| G10 Verträge unvollständig | eingearbeitet | 4.5, 8.1: Satz „vollständig“ (B3), Befehle im Katalog 4 (B11), Konfiguration (B14), Flashen (B7), Pflichtfelder neuer Zeilen und `fw`/`proto` (A4). Punkt 4 (`polls`) entfällt mit dem Wachbetrieb |
| G11 Hauptknopf-Pfad | offen, weil Messung am Pi | P7, M12; `Hauptknopf` kommt über `power.taste_befehl` oder `controls.pin_haupt` (`core-interface.md:221`); Rückfall Z08 ohne `SLEEP` benannt |
| G12 Arbeitspakete | eingearbeitet | 10 (zwei Schritte, Host-Programm als Gegenseite, Modelle, Testliste, Flash-Weg) |
| G13 Lücken im Zustandsmodell | eingearbeitet | Z03 mit Spielt, `OHNE_HOST` (4.1), Hängen bei 5 V als Annahme (3.1), Gute-Nacht-Anzeige 5 % (1.3), Aufwachen bei `leerlauf→aktiv` (3.3 Nr. 6), Z07/E5. „ESP32 weckt, Tobie ist weg“: Box bleibt 10 min bereit, zulässig. Zwangs-Aus bleibt E10 (offen) |
| G14 Vereinfachungen | eingearbeitet, außer `lader` | `lader` bleibt (R4); gestrichen: `wach`, `dur`, `boot_id`, `SLEEP_OK`, `RING`-Muster; Z07/Z17/Z08/Z18 und Z09/Z16 zusammengelegt. Fehlercodes: Anzeige in der Status-Karte offen (B15 nimmt nur `sleep_aborted`) |
| G15 Kleine Fehler | eingearbeitet | `PING` bei neuer Verbindung steht in `reader.py:308`, `:322`; Zahl der offenen Fragen stimmt (Abschnitt 9); Verweis `review_goldfisch.md` mit Pfad in der Kopfzeile; Zeitziel 10 s mit Rückfall 15 s (E13) in 6.1 |
| H-G1 TVDD | eingearbeitet, Variantenwahl offen bis M0 | 5.3 (P3), M0, M4; Abgleich vor jedem Einschlafen in 4.2 |
| H-G2 D+-Rückspeisung | eingearbeitet, Messung offen | 5.2 (P4), M7 |
| H-G3 Fehlimpuls Pad 10 | eingearbeitet | 4.3 (P2) |
| H-G4 „kurz, dann lang“ | eingearbeitet | 4.3: Anti-Mistouch bleibt, Nachbilden nur wenn M1 es verlangt |
| H-G5 SuperMini-Ruhestrom | eingearbeitet | 5.1 (R7), M3 |
| H-G6 Regler, Dropout, Spitzen | eingearbeitet | 5.1 (P10), M2 |
| H-G7 Pad-10-Schalter | eingearbeitet | 5.4 |
| H-G8 Ring-Schalter | eingearbeitet | 5.5, 3.3 Nr. 7, 3.4 |
| H-G9 Tiefschlaf-Firmware | eingearbeitet | 4.4 |
| H-G10 LPCD-Belege | eingearbeitet | LPCD nur in Aus (R2), 4.1 (Firmware ≥ 4.0), Wächterstrom in Abschnitt 7, M4 mit 24 h |
| H-G11 Pinplan | eingearbeitet | 5.6 (P11). Abweichung: siebter Pin GPIO 4, weil `VBUS_SENSE` in P11 fehlt |
| H-G12 Teiler `VBUS_SENSE` | eingearbeitet | 5.2 (100 kΩ / 150 kΩ, 10 nF) |
| H-G13 Budget, Messliste | eingearbeitet | Abschnitt 7 und 10.3 (µA-Messgerät, Rückwirkung auf PiSugar in M2, Einbruch M11, kalt in M3, 24 h in M4, getrennte Zeiten M10) |
| H-G14 Zeitaussagen | eingearbeitet | 6.1 (P9), 1.3 |
| H-G15 A Hall-Sensor | eingearbeitet | R6, 4.2, 5.6, M6 |
| H-G15 B Ring-Weiche | eingearbeitet | R1, Abschnitt 3 |
| H-G15 C `wach` auslassen | durch Resolve entfallen | R2 |
| H-G15 D Lastschalter, PhotoMOS | eingearbeitet | 5.4, 5.5 |
| H-G15 E normales Kabel mit VBUS | offen, weil Messung | 5.2, M7 |
