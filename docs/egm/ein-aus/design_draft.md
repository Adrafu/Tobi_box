# Ein- und Ausschalten: Design-Entwurf (EGM Schritt 2)

*   **Datum:** 10.11.2026
*   **Status:** Entwurf zur Prüfung durch Goldfische. Nichts umgesetzt; kein Vertrag, kein Design, kein Plan, kein Code geändert.
*   **Grundlage:** `concepts_brief.md` (E1 bis E7), `brainstorm.md`, `research.md` (alle im selben Ordner);
    `docs/egm/ladestation/software_folgen.md` Abschnitt 10 (S1 bis S11), `resolve.md` (R8, R10);
    ruhender Entwurf `docs/egm/start-am-lader/design_draft.md` und `review_goldfisch.md`.
    Bestand: `docs/designs/box-software.md`, `docs/protocol/*`, `docs/data-model.md`, `docs/plan/stueckliste-und-psp.md`,
    `firmware/tobibox-reader/`, `box/src/tobibox/`.
*   **Zeichen:** [Schätzung] = Rechnung oder Annahme, nicht gemessen. „Muster“ = Breadboard oder Probeaufbau mit PiSugar.
    Im Code heißt ein Tobie `figur`.
*   **Namen:** *Spielt* = Pi-Zustand `aktiv` (es wird etwas gespielt, `idle.py:105-107`). *Bereit* = `leerlauf`
    (nichts wird gespielt, der Dienst läuft). *Aus* = Pi stromlos, kein Zustand des Dienstes. Die technischen Namen
    in `ZustandMelden.strom` bleiben (`core-interface.md:320`); die Wörter Spielt, Bereit, Aus stehen nur in den Dokumenten.

---

## 0. Kurzfassung

1.  **Drei Zustände, wenige Regeln.** Bereit läuft ohne Frist, solange Strom am Eingang liegt; sonst 10 min nach dem
    letzten Spielen oder Bedienen, dann Aus. Ein Hauptknopf-Druck, Strom am Eingang oder ein aufgelegter Tobie
    holt die Box aus Aus.
2.  **Der ESP32 ist der Wächter.** Er hängt am Akku (PiSugar-Pad BAT), schläft tief, der PN5180 lauscht per LPCD.
    Er „drückt“ den PiSugar-Taster (Pad 10), zeigt sofort das Lauflicht und sagt dem Pi, warum er geweckt wurde.
3.  **Ring über den ESP32 (E7).** Der Pi sendet **Zustandsbefehle** (`RING mode=breathe …`), keine Einzelbilder.
    Atmen, Blinken, Lauflicht rechnet der ESP32 selbst; `led.py` bleibt die Logik und entscheidet nur, welcher
    Befehl gilt. Ein MOSFET macht den Ring in Bereit stromlos.
4.  **Vertrag `reader-v1` bleibt Version 1.** Alles ist additiv (optionales Feld `caps`, neue Zeilen, neue Fehlercodes).
    `firmware_min` steigt auf 2.0.0, weil die Hardware anders ist. 26 Vertragsstellen (Abschnitt 8).
5.  **Schneller Start:** Arbeitspaket mit Zielen *Lauflicht ≤ 1,5 s*, *Frühton ≤ 5 s*, *Hörspiel ≤ 10 s* nach dem Auflegen.
    Der Frühton kommt von einem eigenen frühen Systemdienst; der Box-Dienst weiß davon (`Bereit.fruehton`) und spielt
    dann keinen zweiten Start-Ton.
6.  **Aus „Start am Lader“ gilt weiter:** R8, S1, S4, S5, S7 bis S11 (angepasst). **Es entfallen:** Kurz-Modus (S2, S3),
    Wiederholung des Start-Syncs, Schleifenbremse, `Bereit.einschalten`, „erste Messung vor Bereit“, Update vormerken
    (S6). Begründung: Am Sockel ist die Box immer an (Abschnitt 8.3).
7.  **Typischer Tag ohne Sockel [Schätzung]:** rund 8 bis 10 Wh von 15 Wh (Abschnitt 7).
8.  **Neun offene Fragen** für Tobias (Abschnitt 9), die wichtigsten: E4 (Neustart am Sockel), E9 (Frist ab Abziehen),
    E12 (Rückfall, wenn LPCD durch den Deckel nicht trägt).

---

## 1. Zustandsmodell

### 1.1 Die drei Zustände und was in ihnen läuft

| | **Spielt** | **Bereit** | **Aus** |
|---|---|---|---|
| Pi, `tobiboxd`, MPD | laufen | laufen | aus (PiSugar-Ausgang 5 V aus, Hibernate) |
| Verstärker | an (Stream läuft) | aus (Kernel-Overlay hält SD_MODE, `stueckliste-und-psp.md:50-54`) | stromlos |
| Ring | läuft/Gute Nacht (an) | **stromlos** (MOSFET), Ausnahmen: Lernmodus, kurzes Aufleuchten (1.3) | stromlos (5-V-Schiene aus) |
| Leser | Dauerabfrage 200 ms (`timing.h:9`) | liegt ein Tobie: Dauerabfrage; sonst LPCD-Wachbetrieb (E2, wenn Muster passt) | PN5180 im LPCD, ESP32 im Tiefschlaf |
| Leistung [Schätzung] | 1,6 bis 1,9 W (`stueckliste-und-psp.md:378`) | 1,0 bis 1,3 W (Brief) | 0,001 bis 0,007 W (Abschnitt 7) |
| Frist | – | 10 min ohne Strom, sonst keine | – |

### 1.2 Übergänge

Spalten: Auslöser, Bedingung, Aktion, Folgezustand. „SLEEP“ ist der neue Befehl an den ESP32 (Abschnitt 4).
„Strom“ heißt Strom am Eingang des PiSugar aus **irgendeiner** Quelle (`power.py:156-162`, S10). „Unbekannt“
(`pisugar-server` antwortet nicht, `am_lader = None`) zählt wie **kein Strom**: sicher für den Akku, `power.py` warnt schon.

**Aus verlassen**

| # | Auslöser | Bedingung | Aktion | Folge |
|---|---|---|---|---|
| Z01 | **Tobie aufgelegt** (LPCD, ESP32) | `lpcd=1` (Standard), eine gültige Lesung (`uid` oder `gesperrt`), kein Tiefstand | ESP32 pulst Pad 10, startet das Lauflicht (Helligkeit aus `SLEEP`), `WAKE reason=tobie`; Pi bootet; bei `Bereit` gilt CUJ 20 | Hochfahren, dann **Spielt** (Leise-Zeit „stumm“: **Bereit**, E5) |
| Z02 | **Hauptknopf** (PiSugar-Taster) | – | PiSugar schaltet ein; 5 V am USB wecken den ESP32; Lauflicht; Pi bootet; liegender Tobie spielt (CUJ 20) | Hochfahren, dann **Bereit** (liegt ein Tobie: Spielt) |
| Z03 | **Strom am Eingang kommt** (Andocken R8, Kabel, Powerbank) | PiSugar „Einschalten bei Strom“ an (E4) | wie Z02; Ring zeigt nach `Bereit` den Ladestand (5 s); Sync prüfen (S8) | Hochfahren, dann **Bereit** (bleibt, Strom da) |
| Z04 | Tobie aufgelegt nach Tiefstand | `lpcd=0` (vom Pi vor dem Tiefstand-Aus gesetzt) | nichts; nur Z02 und Z03 wecken | **Aus** |
| Z05 | Hochfahren fertig (`Bereit` im Dienst) | – | Idle-Zähler beginnt; Frühton-Marke wird verbraucht (`fruehton`, Abschnitt 6.4); das Lauflicht des ESP32 endet mit dem ersten `RING` des Pi | **Bereit** oder **Spielt** |

**Spielt verlassen**

| # | Auslöser | Bedingung | Aktion | Folge |
|---|---|---|---|---|
| Z06 | Folge zu Ende, Pause (Hauptknopf kurz), Abheben, „stumm“-Fenster beginnt, Gute Nacht zu Ende (CUJ 14) | – | Zeiger gespeichert; liegt ein Tobie: Ring zeigt Pause 10 s, dann stromlos; sonst sofort stromlos. Frist: 10 min ab jetzt, wenn kein Strom | **Bereit** |
| Z07 | Hauptknopf lang | immer | Zeiger speichern, Ring aus, `SLEEP`, `poweroff` | Herunterfahren → **Aus** |
| Z08 | Akku-Tiefstand (5 %, Hysterese 3 %, `power.py:32`, `:291-309`) | **kein Strom**; gilt auch bei Sync und Update | Sync abbrechen, Ton `akku_leer`, Zeiger speichern, `CFG lpcd=0`, `SLEEP`, `poweroff` (`idle.py:252-259`) | → **Aus** (Tobie weckt nicht mehr) |
| Z09 | Andocken oder Abziehen | – | nur Ring (S9): Ladestand 5 s; Sync prüfen beim Andocken (S8) | **Spielt** |
| Z10 | **Dienst-Neustart** (Update, Absturz) | gleiche Boot-ID (Entscheidung G, `bootid.py:3-4`, `lauf.py:6-9`) | der ESP32 bleibt wach, Pi-Zustand wie vor dem Neustart; liegender Tobie spielt **nicht** von selbst; kein Frühton (Dienst läuft, kein Einschalten); Ring: Lauflicht nur nach den Leise-Regeln | gleich |

**Bereit verlassen**

| # | Auslöser | Bedingung | Aktion | Folge |
|---|---|---|---|---|
| Z11 | **Tobie aufgelegt** oder Hauptknopf kurz (Play) | nicht „stumm“ (dann `gehalten`, Hinweiston, CUJ 15) | LPCD → Dauerabfrage → Hörspiel, Ziel ≤ 1,5 s, Grenze 3 s (Brief) | **Spielt** |
| Z12 | Bedienung: Hauptknopf kurz, Weiter, Zurück, Drehregler, Kopfhörer | – | Frist neu (`idle.py:186-190`); Ring leuchtet 3 s auf (E6) | **Bereit** |
| Z13 | **Frist um** (10 min) | **kein Strom**; kein Lernmodus, kein Sync, kein Update | Zeiger speichern, Ring aus, `SLEEP`, `poweroff` | → **Aus** |
| Z14 | Frist um | Lernmodus, Sync oder Update läuft | warten; nach dem Ende sofort prüfen (Lernmodus: Frist neu, `idle.py:238-242`) | **Bereit** |
| Z15 | **Strom kommt** (Andocken bei laufender Box) | Wechsel von „kein Strom“ nach „Strom“ nach `Bereit`, mindestens 10 s nach der letzten Rückmeldung | Frist wird **verworfen**; Ring Ladestand 5 s; Ton `lader` (nicht in „leiser“, „stumm“, bei unsicherer Uhr); Sync prüfen einmal je Andocken (S8) | **Bereit** ohne Frist |
| Z16 | **Strom weg** (Abziehen) | – | Ring Akku 5 s (Ampelfarben, kein Ton); Frist 10 min **ab jetzt** (E9); Tiefstand wieder scharf | **Bereit** mit Frist |
| Z17 | Hauptknopf lang | immer | wie Z07. Am Sockel kann der PiSugar sofort neu starten (E4); gewollt, wenn es so ist | → **Aus** (oder Neustart) |
| Z18 | Akku-Tiefstand | kein Strom | wie Z08 | → **Aus** |
| Z19 | Leise-Zeit beginnt oder endet | – | Zustand ändert sich nicht; Ring-Helligkeit (3.5); Tobie in „stumm“: `gehalten` (CUJ 15). Die Frist läuft weiter (Entscheidung O) | **Bereit** |
| Z20 | Lernmodus läuft | – | hält Bereit (kein Aus); Ring Lernen (blaues Atmen) bleibt an; Ende: Frist neu | **Bereit** |
| Z21 | Sync oder Update läuft | Update nur mit Strom und `home` (`idle.py:153-165`) | hält Bereit | **Bereit** |
| Z22 | Herunterfahren hat nicht gewirkt (`HerunterfahrenFehlgeschlagen`, B1) | `poweroff` meldet Fehler | Hinweis an HA, Frist neu (`idle.py:322-343`); der ESP32 bricht das Schlafen nach `SLEEP_WARTEN_S` ab (`ERR code=sleep_aborted`) | **Bereit** / **Spielt** |

### 1.3 Regeln, die quer durch die Tabelle gelten

*   **Frist = LEERLAUF_S = 600 s** (`idle.py:57` heute 1200). Sie zählt, wenn nichts gespielt wird, **auch mit liegendem Tobie**
    (Entscheidung O bleibt, `box-software.md:532-537`). Sie zählt nur **ohne Strom** (und bei „unbekannt“). Mit Strom ist `faellig` nie wahr.
*   **Bedienung** setzt die Frist neu (Z12), HA-Befehle nicht (`idle.py:12-14`, unverändert).
*   **Ring in Bereit:** stromlos. Es leuchtet auf: 3 s nach Bedienung, Auflegen, Abheben (zeigt den neuen Zustand); 5 s Akku nach Andocken
    und Abziehen; 10 s Pause nach Z06 bei liegendem Tobie; Lernmodus dauernd. Das ändert `led.py:270-271` (heute zeigt der Ring in
    `leerlauf` mit liegendem Tobie dauernd Pause).
*   **Verstärker** braucht keine neue Regel: Ohne Stream hält das Overlay SD_MODE tief (`stueckliste-und-psp.md:50-54`, 0,6 µA im Shutdown, `research.md:99`).
*   **Zeitgrenzen:** Aus → Lauflicht ≤ 1,5 s (Tobie) bzw. ≤ 0,5 s (Knopf, Strom); Bereit → Hörspiel ≤ 3 s (Tobias), Ziel 1,5 s;
    Aus → Hörspiel ≤ 10 s (Abschnitt 6). Die Grenze 1,0 s in `docs/timing.md` gilt weiter für die Dauerabfrage (Spielt und Bereit mit liegendem Tobie).
*   **Leise-Zeiten** ändern nie den Zustand, nur Ton und Ring (3.5, CUJ 15).

---

## 2. CUJs

Schreibweise wie im Design. Neu sind **CUJ 21 bis 25**. Geändert sind CUJ 10, 15, 16, 18, 20 (2.2). Die Nummern 21 und 22 des ruhenden
Entwurfs `start-am-lader` werden nicht vergeben.

### 2.1 Neue CUJs

**CUJ 21: Hochfahren mit sofortigem Lauflicht**
*   **Given**: Die Box ist aus. Der ESP32 schläft, der PN5180 lauscht.
*   **When**: Ein Tobie wird aufgelegt, oder der Hauptknopf wird gedrückt, oder Strom kommt an den Eingang.
*   **Then**:
    1.  Der ESP32 wacht auf (LPCD-Meldung bzw. 5 V am USB) und zeigt das weiße Lauflicht: nach dem Auflegen **≤ 1,5 s**, nach Knopf oder Strom ≤ 0,5 s.
        Nachts (Leise-Zeit oder unsichere Uhr beim Einschlafen der Box) ist es gedimmt oder aus (3.5).
    2.  Der Frühdienst spielt den Ton `start`, sobald ALSA da ist (Ziel ≤ 5 s nach dem Strom am Pi), nur im Modus „normal“ bei sicherer Uhr.
    3.  Der Box-Dienst meldet `Bereit` (Ziel ≤ 8,5 s nach dem Strom am Pi). Er spielt **keinen** zweiten Start-Ton (`fruehton`).
        Das erste `RING` des Pi beendet das Lauflicht des ESP32.
    4.  Liegt ein Tobie, spielt er wie in CUJ 20; unter „stumm“ gilt CUJ 15. Das Hörspiel beginnt **≤ 10 s nach dem Auflegen**.
*   **Ausnahme Pi stumm:** Kommt der Pi nicht hoch (kein `PING` binnen 30 s), endet das Lauflicht, der Ring wird dunkel, `ERR code=host_timeout`
    beim nächsten Kontakt. Die Box zieht weiter Strom (E10).

**CUJ 22: Tobie weckt die ausgeschaltete Box**
*   **Given**: Die Box ist aus (nach Frist, Hauptknopf lang oder Tiefstand-Aus). `lpcd=1`.
*   **When**: Ein Tobie wird aufgelegt.
*   **Then**: LPCD meldet eine Feldänderung. Der ESP32 prüft **mit einer Lesung**, ob eine Karte oder ein Tonie liegt. Hand oder Metall wecken nicht
    (nach 3 Fehlmeldungen in 10 s wird das Intervall vervierfacht und neu abgeglichen). Dann CUJ 21. Der Tobie, der geweckt hat, spielt sofort (CUJ 20, Boot-ID neu).
*   **Abheben und neu Auflegen** weckt ebenfalls: Lag der Tobie beim Ausschalten schon da, wurde LPCD mit ihm abgeglichen. Das Abheben löst eine Meldung aus,
    der ESP32 gleicht neu ab; das Auflegen weckt dann.
*   **Rückfall (E12):** Trägt LPCD durch den Deckel nicht, weckt nur der Hauptknopf (Z02) oder Strom (Z03). CUJ 21 bleibt gültig.

**CUJ 23: Box steht am Sockel bereit**
*   **Given**: Die Box steht am Sockel (Strom am Eingang), egal ob Tag oder Nacht.
*   **When**: Ein Kind legt einen Tobie auf, oder drückt den Hauptknopf.
*   **Then**: Die Box ist bereit (Bereit ohne Frist), es spielt in ≤ 3 s (Ziel 1,5 s). Sie schaltet sich **nie von selbst** aus (Z13 braucht „kein Strom“).
    Der Ring ist dunkel; nachts gelten die Leise-Zeiten (CUJ 15). Sync läuft im Takt, ein Update kann HA jederzeit schicken (CUJ 10).
    Der Akku steht am Sockel dauernd bei 100 % (E3).

**CUJ 24: Pause ohne Sockel, nach 10 min aus**
*   **Given**: Die Box ist nicht am Sockel. Ein Hörspiel ist zu Ende, pausiert oder abgehoben. Es läuft kein Lernmodus, kein Sync, kein Update.
*   **When**: 10 min lang wird nichts gespielt und nichts bedient (ein liegender Tobie zählt nicht, Entscheidung O).
*   **Then**: Zeiger gespeichert, Ring aus, `SLEEP`, Herunterfahren; der PiSugar schaltet ab; der ESP32 geht schlafen. Wird in den 10 min ein Tobie aufgelegt oder ein
    Knopf gedrückt, spielt die Box in ≤ 3 s (Bereit). Danach: CUJ 22. Mit Gute Nacht (CUJ 14) ist die Box nach Timer, Ausblenden und 10 min aus.

**CUJ 25: Andocken und Abziehen**
*   **Given**: Die Box steht nicht am Sockel; Strom kommt an den Eingang (Sockel, Kabel, Powerbank; die Box unterscheidet sie nicht, S10).
*   **When**: Strom kommt (Andocken, R8) oder geht (Abziehen).
*   **Then**:

    | Lage | Andocken | Abziehen |
    |---|---|---|
    | **Aus** | Box startet (CUJ 21), Frühton `start`, nach `Bereit` Ring Ladestand (blau, 5 s), Sync prüfen (S8). Danach Bereit ohne Frist | – |
    | **Bereit** | Ring Ladestand 5 s, Ton `lader` (nicht „leiser“, „stumm“, unsichere Uhr, Lernmodus), Sync prüfen. Frist verworfen | Ring Akku 5 s, kein Ton, Frist 10 min ab jetzt |
    | **Spielt** | nur Ring 3 s (S9), kein Ton; Sync prüfen | nur Ring |
    | Update läuft | nur Ring, kein Sync | – |

    Die Rückmeldung hat eine Sperre von 10 s (S8): Wackelt der Kontakt, kommt die erste Rückmeldung sofort, weitere frühestens 10 s später, **auch im Ring** (anders als im ruhenden Entwurf, G5).
    Liegt beim Andocken aus Aus ein Tobie auf der Box, spielt er (S4, CUJ 20); nachts schützt „stumm“.

### 2.2 Geänderte CUJs (Wortlaut)

**CUJ 16: Leerlauf-Abschaltung → „Bereit und Aus“** (ersetzt `box-software.md:855-868`):

> *   **Given**: Es läuft keine Wiedergabe. Die Box ist bereit (Pi und Dienst laufen, Verstärker und Ring aus, Leser lauscht sparsam).
> *   **When**: Am Eingang liegt **kein Strom** und 10 min vergehen, in denen nichts gespielt und nichts bedient wird.
> *   **Then**: Die Box fährt herunter und ist aus — außer es läuft ein Sync, ein Update oder der Lernmodus: dann wartet sie.
>     **Mit Strom am Eingang bleibt die Box bereit und schaltet nie von selbst ab.** Kommt der Strom, während die Frist läuft, wird sie verworfen;
>     geht er, beginnt eine neue Frist von 10 min. Bedienung (Taste, Drehregler, Hauptknopf kurz, Kopfhörer) beginnt die Frist neu, HA-Befehle nicht.
>     Auch ein liegender Tobie hält die Box nicht an (Entscheidung O). Schlägt das Herunterfahren fehl, läuft die Box weiter, die Frist beginnt neu
>     und HA bekommt einen Hinweis (Befund B1). Ein Tobie, der Hauptknopf (Z02) oder Strom (Z03) holen die Box aus Aus. In der Simulation wird das
>     Herunterfahren nur protokolliert. Der PiSugar-Wecker (Zeit-Wecken) ist nicht Teil dieses Konzepts.

**CUJ 10: Software-Update** (`box-software.md:789-797`). Zusatz: „Am Sockel ist die Box immer bereit; HA kann das Update jederzeit schicken. Ein Merker ‚beim nächsten Andocken‘ ist nicht nötig.“ Klarstellung: ‚am Lader‘ heißt Strom am Eingang aus jeder Quelle.

**CUJ 15: Leise-Zeiten** (`box-software.md:837-853`). Zusatz: „Der Ton `lader` und der Frühton `start` entfallen unter ‚leiser‘, ‚stumm‘ und bei unsicherer Uhr.
Der Ring zeigt die Akku-Anzeige gedimmt (5 % ‚leiser‘, 3 % ‚stumm‘). Das Lauflicht beim Wecken ist gedimmt oder aus (3.5).“

**CUJ 18: LED-Ring-Zustände** (`box-software.md:881-898`). Zusatz: „Der Ring hängt am ESP32 (E7). In Bereit ist er stromlos und leuchtet nur kurz (Abschnitt 1.3). Das Lauflicht beim Aufwachen
läuft auf dem ESP32, noch bevor der Pi bereit ist. Die Helligkeit liegt nie über 25 %; der Deckel gilt auch in der Firmware.“

**CUJ 20: Tobie liegt schon beim Start** (`box-software.md:919-934`). Zusatz bei *Given*: „… oder der Tobie hat die Box geweckt (CUJ 22)“. Zusatz bei *Then*: „Beim Wecken durch einen Tobie
läuft vorher das Lauflicht (CUJ 21). Liegt ein Tobie beim Andocken aus Aus, gilt dasselbe (S4).“ Die Ausnahme Dienst-Neustart bleibt wörtlich.

---

## 3. Ring über den ESP32 (E7)

### 3.1 Aufteilung

| Was | Wer | Warum |
|---|---|---|
| Welcher Zustand gilt (läuft, Pause, Akku, Lernen, Gute Nacht, Aufwachen, aus), Farben, Zeiten, Leise-Dimmung | **Pi, `led.py`** (`LedLogik`, `led.py:182-283`) | Logik und Tests bleiben; Simulation und GUI nutzen sie weiter |
| Einzelbilder der Animationen (Atmen, Blinken, Lauflicht, Füllstand) | **ESP32** | siehe 3.3 |
| Lauflicht beim Wecken, **bevor** der Pi spricht | **ESP32 allein** | der Pi läuft noch nicht |
| MOSFET des Rings (an, wenn der Ring leuchtet; aus nach `RING_AUS_VERZ_MS` Dunkelheit) | **ESP32** | Strom sparen ohne Zutun des Pi |
| Helligkeitsdeckel 25 % | **ESP32 und Pi** (`led.py:29`) | Schutz des Netzteils auch bei einem Fehler des Pi (Plan Punkt 8: voll weiß 2,4 A) |
| 5-Bit-Stufe und Feinskalierung der APA102-Helligkeit | **ESP32** | löst die Rundung `int(helligkeit × 31 / 100)` (`led.py:114`: 3 % ergibt Stufe 0, dunkel); Stufe mindestens 1, der Rest über die Farbwerte |

### 3.2 Befehle (Pi → ESP32)

Eine Zeile `RING`, Felder nach `reader-v1.md` Abschnitt 2 (ein Leerzeichen, `schluessel=wert`). Alle Felder außer `mode` sind optional und haben Vorgaben.

| Feld | Werte | Bedeutung |
|---|---|---|
| `mode` | `off` `solid` `breathe` `blink` `comet` `fill` `frame` | Muster |
| `col` | 6 Hexzeichen `RRGGBB` | Farbe (Vorgabe `ffffff`) |
| `br` | 0 bis 100 | Helligkeit in Prozent; bei `breathe` der untere Punkt. Der ESP32 klemmt auf `RING_DECKEL_PROZENT` (25) |
| `br2` | 0 bis 100 | oberer Punkt bei `breathe` |
| `per` | 100 bis 60000 (ms) | Periode (Atmen, Blinken) bzw. Dauer einer Runde (Lauflicht) |
| `n` | 0 bis 40 | bei `fill`: Zahl der leuchtenden LEDs; bei `comet`: Zahl der Runden (0 = endlos) |
| `dur` | 100 bis 600000 (ms) | nach so langer Zeit geht der Ring von selbst aus (nur Anzeigen mit Ende: Akku 5 s, Lauflicht 2 s) |
| `data` | base64url ohne Padding | nur bei `frame`: 40 × RGB = 120 Byte = 160 Zeichen |

Abbildung der Zustände von `led.py` (Spalte „Pi sendet“):

| `led.py` | Pi sendet |
|---|---|
| läuft (`led.py:130-133`) | `RING mode=breathe col=00ff46 br=12 br2=25 per=6000` |
| Pause (`:136-137`) | `RING mode=solid col=ff6e00 br=10` |
| Akku-Anzeige (`:161-168`) | `RING mode=fill col=<grün/gelb/rot/blau> br=15 n=<LEDs> dur=5000` |
| Tiefstand (`:162-164`) | `RING mode=blink col=ff0000 br=25 per=500` |
| unbekannte Karte (`:152-154`) | `RING mode=blink col=ff0078 br=25 per=500 dur=1000` |
| Lernmodus (`:140-142`) | `RING mode=breathe col=0046ff br=8 br2=25 per=3000` |
| Gute Nacht (`:145-149`) | `RING mode=breathe col=ff5a0a br=<3·f> br2=<8·f> per=4000`, neu gesendet mit dem Ausblende-Faktor `f` etwa einmal je Sekunde |
| Aufwachen (`:171-179`), nur nach Dienst-Neustart | `RING mode=comet col=ffc878 br=25 per=1000 n=2` |
| aus | `RING mode=off` |
| Bild für Tests, Simulation, Sonderfälle | `RING mode=frame br=<n> data=<…>` |

Der Pi sendet bei jedem Wechsel des Musters **und alle `RING_KEEPALIVE_S` = 5 s dieselbe Zeile erneut**. Die Wiederholung dient dem ESP32 als Lebenszeichen (3.4) und heilt eine verlorene Zeile
(die Firmware verwirft Zeilen, wenn niemand liest, `reader-v1.md:25-26`). Die Wiederholung startet das Muster **nicht neu**, wenn Parameter und Muster gleich sind (kein Ruckeln).

### 3.3 Atmen und Blinken lokal oder Bild für Bild? (Begründung)

| | Bild für Bild vom Pi | **Muster-Befehle (Empfehlung)** |
|---|---|---|
| Bandbreite | `LED_TAKT_S` = 0,1 s (`app.py:77`): 10 Zeilen/s zu je ≤ 190 Zeichen (Grenze 200, `reader-v1.md:46`) ≈ 1,9 kB/s = 15 kbit/s. Das trägt USB-CDC leicht | ein Befehl je Wechsel (≈ 70 Zeichen) plus 1 Zeile je 5 s |
| Pi-Last | 10 Aufweckungen/s dauerhaft, solange etwas atmet (Spielt: stundenlang) | praktisch null |
| Lauflicht beim Wecken | muss **trotzdem** im ESP32 stecken (Pi läuft noch nicht): die Engine entsteht ohnehin | dieselbe Engine |
| Flüssigkeit | 10 Bilder/s, gerade genug für das Atmen, Lauflicht ruckelt | 50 Bilder/s im ESP32, unabhängig vom Pi |
| Pi hängt | Ring friert auf dem letzten Bild | Ring läuft bis `RING_TIMEOUT_S`, dann aus (3.4) |
| Preis | Python-Code unverändert | die Muster stehen **zweimal** (Python als Referenz für Simulation, C++ im ESP32) |

Der Preis wird bezahlt mit einem Gleichheitstest: Die Referenz in `led.py` (`ring_fuer`) erzeugt Prüfbilder zu festen Zeitpunkten (JSON), die Firmware-Tests (`pio test -e native`)
mit der C++-Engine vergleichen (Toleranz ±2 je Farbwert). `mode=frame` bleibt als Notausgang und für Tests.

### 3.4 Was der ESP32 selbst entscheidet

| Lage | Verhalten |
|---|---|
| **Wecken** (Z01 bis Z03) | Sofort Lauflicht (`comet`, warmweiß, `RING_WECK_HELL`, 2 Runden je 1 s, endlos wiederholt), MOSFET zuerst an, dann Daten. Es endet mit dem ersten `RING` des Pi, spätestens nach `WECK_LAUFLICHT_MAX_S` = 30 s |
| **Helligkeit des Lauflichts** | Aus dem letzten `SLEEP` (`wring`, `wring_s`, 4.4): so lange `wring_s` nicht abgelaufen ist (Zeit der ESP32-RTC), gilt `wring` (0 = aus). Danach der sichere Wert `RING_WECK_SICHER` = 5 %. Die RTC des ESP32 ist ungenau (kein Quarz); deshalb nur Prozentwert und Dauer, keine Uhrzeit |
| **Pi spricht nicht** | Nach 30 s ohne `PING`: Ring dunkel, MOSFET aus, `ERR code=host_timeout`; sonst keine Aktion (E10 fragt nach dem Zwangs-Aus) |
| **Pi stirbt im Betrieb** (Ring nicht mehr erneuert) | Kein `RING` und kein `PING` seit `RING_TIMEOUT_S` = 15 s: Ring dunkel, MOSFET aus. Ein neues `RING` schaltet wieder ein |
| **Ring aus** | `RING mode=off` oder `dur` abgelaufen: beide Datenleitungen auf **Low**, nach `RING_AUS_VERZ_MS` = 1000 ms der MOSFET aus. Ohne diesen Schritt würde der Ring über die Datenleitungen halb versorgt (Muster, 5.5) |
| **Tiefschlaf** | MOSFET aus, Leitungen Low gehalten (`gpio_hold`), Ring stromlos |
| **Deckel** | Jeder Befehl wird auf 25 % geklemmt |

### 3.5 Helligkeitsstufen und Leise-Zeiten

| `ruhe` | Akku-Anzeige (Andocken, Abziehen, Start) | Lauflicht beim Wecken | übrige Zustände |
|---|---|---|---|
| `normal`, Uhr sicher | 15 % (heute `led.py:168`) | 25 % | wie heute |
| `leiser` | **5 %** (neu) | **aus** | wie heute |
| `stumm` | **3 %** (neu, absolut) | **aus** | alles × 0,4 (`led.py:64, 280-283`, unverändert) |
| Uhr unsicher (`zeit_ok` falsch) | 5 % | aus | wie heute |

*   Die Werte 5 % und 3 % gelten **nur** für die Akku-Anzeige und werden vom Faktor 0,4 ausgenommen (sonst 1,2 % = dunkel; G6.1 des Reviews).
*   Das Lauflicht des **Pi** (nur nach Dienst-Neustart) folgt derselben Spalte, auch nach einem Update-Neustart (G6.3).
*   Für das Lauflicht **des ESP32** kennt der ESP32 die Leise-Zeiten nicht. Der Pi schickt vor dem Herunterfahren `wring` und `wring_s`: ist jetzt Leise-Zeit,
    `wring` = 0 oder 5 und `wring_s` = Sekunden bis zum Ende des Fensters; sonst 25 und Sekunden bis zum Beginn des nächsten Fensters. Danach gilt 5 %
    (dunkel genug für nachts, sichtbar am Tag). Ist die Uhr unsicher: `wring` = 5, `wring_s` = 0.
*   Sichtbarkeit von 3 % und 5 % durch das Gehäuse: Messung am Muster (Abschnitt 10, Messliste 9).

### 3.6 Entprellen des Rings

Der ruhende Entwurf ließ den Ring bei wackelndem Kontakt flackern (G5). Hier: `LedLogik.akku_zeigen` ignoriert einen Laderwechsel, wenn die letzte Anzeige weniger als `LADER_SPERRE_S` = 10 s her ist.
Das bleibt im Pi (`led.py`), kein Vertrag.

---

## 4. Leser-Firmware

### 4.1 Zustände des ESP32

| Zustand | Was läuft | Weckquellen / Übergänge |
|---|---|---|
| `SCHLAF` | Tiefschlaf (7 µA, `research.md:78`), PN5180 im LPCD, MOSFET und Pad-Schalter aus, Leitungen Low gehalten | LPCD-IRQ → `PRUEFEN`; 5 V am USB (VBUS) → `WECKEN`; Strom am Eingang (STROM_IN, falls gebaut) → `WECKEN` |
| `PRUEFEN` | PN5180 starten, **eine** Lesung | gültig → Pad 10 pulsen, `WECKEN`; sonst Neuabgleich, zurück in `SCHLAF` (nach 3 Fehlmeldungen in 10 s Intervall × 4) |
| `WECKEN` | Lauflicht, wartet auf Host (USB offen, erstes `PING`) | `PING` → `LAEUFT`; 30 s ohne `PING` → Ring aus, `ERR host_timeout`; VBUS weg → `SCHLAF` |
| `LAEUFT` | Betrieb: Dauerabfrage (200 ms) oder LPCD-Wachbetrieb (`CFG wach=1`, nur wenn kein Tobie liegt); `RING`-Befehle | `SLEEP` → `ABSCHALTEN`; VBUS weg ohne `SLEEP` länger als `VBUS_WEG_ENTPRELL_MS` (3 s) → `SCHLAF` |
| `ABSCHALTEN` | wartet auf VBUS aus (Pi ist aus); Ring aus | VBUS weg → `SCHLAF`; nach `SLEEP_WARTEN_S` = 90 s VBUS noch da → `ERR sleep_aborted`, zurück `LAEUFT` (Z22) |

*   **Wie der ESP32 merkt, dass der Pi läuft:** (1) Pegel „5 V am USB“ an einem Eingang (Teiler, Abschnitt 5.2); (2) ein offener USB-Port mit `PING` (der Box-Dienst sendet es bei jeder neuen Verbindung, `reader.py:213`, `reader-v1.md:285`).
    Es gibt keinen Herzschlag Pi → ESP32; „Pi hängt, aber 5 V da“ erkennt der ESP32 nur am ausbleibenden `RING` (3.4).
*   **Wann der ESP32 schlafen geht:** nur wenn (a) der Pi `SLEEP` gesagt hat **und** VBUS weg ist, oder (b) VBUS ohne Ansage 3 s weg ist (Hauptknopf lang erzwungen, Akku leer). Nie vor dem Pi.
*   **LPCD mit PN5180-Firmware < 4.0** geht nicht (`research.md:207`); die Firmware lässt `caps` dann `lpcd` weg (HELLO trägt `pn5180=`, `reader-v1.md:99`).

### 4.2 Wecken des PiSugar über Pad 10

*   Der ESP32 schaltet Pad 10 mit **BAT (Pad 2)** zusammen (nicht Masse, `research.md:187`). Der Schalter ist ein Teil, das in Ruhe keinen Strom leckt (Abschnitt 5.3).
*   **Anti-Mistouch aus**, damit ein kurzer Druck reicht (`research.md:171`). Der Pi setzt das beim Start über `pisugar-server` (`set_anti_mistouch false`, Befehl laut `research.md:191`, Persistenz nach Stromverlust **nicht belegt**) und prüft es bei jedem Start.
*   **Pulsdauer** `PAD_PULS_MS` = 150 [Schätzung]; die Zeiten stehen nirgends (`research.md:191`), Messung 5 im Abschnitt 10 legt sie fest (Bereich 50 bis 500 ms).
*   Der Puls kommt **nach** der Lesung (nicht vorher), damit Hand und Metall nichts auslösen.
*   Kein Rückfall mit „kurz, dann lang“: Ein langer Druck auf eine laufende Box würde sie wieder ausschalten (`research.md:171`).
*   Hauptknopf (Arcade, parallel zum Taster, `stueckliste-und-psp.md:45-48`) und ESP32-Schalter sind parallel; der ESP32-Schalter darf den Knopf nicht beeinflussen.

### 4.3 LPCD im Zustand Bereit (E2)

*   `CFG wach=1`: Ist der Zustand des Entprellers `LEER` (kein Tobie liegt) seit `LPCD_ARM_MS` (2000), geht der PN5180 in den LPCD-Wachbetrieb; der ESP32 bleibt **wach** (USB bleibt stabil, HB läuft weiter).
    Bei einer Feldänderung folgen volle Abfragezyklen wie heute (200 ms, `timing.h:9`); nach `LPCD_RUECK_ZYKLEN` (5) leeren Zyklen zurück in den Wachbetrieb. Der Entpreller bleibt unverändert (`reader-v1.md:299-445`).
*   **Was das spart [Schätzung]:** nur den RF-Puls (≈ 0,045 W bei 10 ms je 200 ms, `research.md:88`). Die 0,17 bis 0,24 W des wachen ESP32-S3 (`research.md:88`) spart erst ein **Light-Sleep**, der die USB-Verbindung gefährden kann.
    Stufe 1 (dieser Entwurf): ESP32 wach bei 80 MHz (22 mA statt 33 mA bei 240 MHz, `research.md:75`), PN5180 im LPCD. Stufe 2 nur, wenn Messung 4 zeigt, dass USB im Light-Sleep hält.
*   **Latenz:** LPCD-Intervall `LPCD_INTERVAL_MS` = 300 [Schätzung]: im Mittel 150 ms, schlimmstenfalls 300 ms vor der ersten Lesung. Zur Rechnung in `box-software.md:1043-1058` (0,94 s) kommen höchstens 0,3 s: ≈ 1,3 s, unter Tobias' 3 s.
*   Liegt ein Tobie (Spielt, oder Bereit mit liegendem Tobie), bleibt die Dauerabfrage; LPCD erkennt Abheben nicht zuverlässig (nicht belegt).
*   Standard `wach=0`, bis Messung 4 passt (E2: „wenn die Messung am Muster passt“).

### 4.4 Vertragsänderungen am Leser-Protokoll (Wortlaut, alt → neu)

Stelle: `docs/protocol/reader-v1.md`. **`proto` bleibt 1.** Begründung (Abschnitt 13 des Vertrags, Zeilen 575 bis 580, und Abschnitt 11, Zeilen 518 bis 523): Neu sind nur ein **optionales** Feld am Ende von `HELLO`,
neue Zeilentypen vom Leser (ältere Dienste ignorieren sie), neue Fehlercodes und neue Zeilen **vom Box-Dienst**, für die Abschnitt 8 den „Rückkanal“ schon reserviert hat (Zeilen 289 bis 293). Eine alte Firmware antwortet auf sie mit
`ERR code=bad_command` (Zeilen 294 bis 296), ohne etwas auszuführen. **`fw` steigt auf 2.0.0** (Pins und Hardware ändern sich), `firmware_min` im Update-Paket auf 2.0.0 (Zeilen 586 bis 589).

**L1, Abschnitt 3, Zeilentabelle (Zeilen 72 bis 79).** alt: sechs Zeilen `HELLO PLACED LOCKED REMOVED HB ERR`. Neu, zwei Zeilen dazu und ein Feld:

| Zeile | Felder in dieser Reihenfolge | Wann |
|---|---|---|
| `HELLO` | `proto` `fw` `build` `pn5180` **`caps`** (optional, am Ende) | beim Start und als Antwort auf `PING` |
| `WAKE` | `reason` `ring` | **einmal** direkt nach dem `HELLO`, das auf das **erste** `PING` nach einem Wecken folgt |
| `SLEEP_OK` | – | als Antwort auf `SLEEP` |

Felder: `caps` = Liste, durch Komma getrennt, aus `ring`, `lpcd`, `sleep`, `wake`; fehlt das Feld, kann die Firmware nichts davon (Firmware 1.x). `reason` ∈ `tobie`, `strom`, `extern`, `reset`
(`extern` = der Pi wurde ohne Zutun des ESP32 eingeschaltet, Knopf oder Strom ohne STROM_IN-Sensor); `ring` = `1`, wenn das Lauflicht des ESP32 gerade läuft, sonst `0`.

**L2, Abschnitt 3, Satz „Alle Felder jeder Zeile sind Pflicht“ (Zeile 81).** alt: „Alle Felder jeder Zeile sind **Pflicht**. Es gibt keine optionalen Felder.“
Neu: „Alle Felder jeder Zeile sind **Pflicht**, außer den in der Tabelle als *optional* gekennzeichneten (heute nur `caps` in `HELLO`).“

**L3, Abschnitt 7, Fehlercodes (Tabelle ab Zeile 231).** Neu, Schwere „Hinweis“ (kein Einfluss auf den Prüfpunkt), ohne `errors` zu erhöhen:

| Code | Bedeutung |
|---|---|
| `sleep_aborted` | `SLEEP` empfangen, aber die 5 V am USB blieben länger als `SLEEP_WARTEN_S`; der ESP32 schläft nicht |
| `host_timeout` | nach dem Wecken kam binnen `WECK_LAUFLICHT_MAX_S` kein `PING` |
| `lpcd_noise` | mehr als 3 Fehlmeldungen des LPCD in 10 s; Intervall vervierfacht |
| `pad_pulse` | Pad 10 gepulst, aber keine 5 V am USB binnen 2 s |

**L4, Abschnitt 8, Zeilen vom Box-Dienst (Zeilen 281 bis 297).** alt: nur `PING`; „Reserviert: Jede andere Zeile vom Box-Dienst ist in Version 1 reserviert … Der Box-Dienst v1 sendet nur `PING`.“ Neu:

| Zeile | Wirkung |
|---|---|
| `PING` | unverändert |
| `RING mode=… [col=…] [br=…] [br2=…] [per=…] [n=…] [dur=…] [data=…]` | setzt das Muster des Rings (Abschnitt 3.2 dieses Entwurfs, in den Vertrag zu übernehmen). Gilt als Lebenszeichen für `RING_TIMEOUT_S`. Antwort: keine |
| `SLEEP wring=<0..25> wring_s=<Sekunden>` | „Der Pi fährt herunter.“ Ring aus. Der ESP32 antwortet sofort `SLEEP_OK`, wartet auf das Ende der 5 V am USB und geht dann schlafen. `wring`: Helligkeit des Lauflichts beim nächsten Wecken; `wring_s`: so lange gilt sie (danach `RING_WECK_SICHER`) |
| `CFG lpcd=<0\|1> wach=<0\|1>` | `lpcd`: darf der Tobie im Zustand `SCHLAF` wecken (im RTC-Speicher gehalten); `wach`: LPCD-Wachbetrieb im Betrieb. Wird nach jedem `HELLO` gesendet |

„Eine Firmware ohne `caps`-Merkmal beantwortet `RING`, `SLEEP` und `CFG` mit `ERR code=bad_command`. Der Box-Dienst sendet sie nur, wenn `caps` das Merkmal (`ring`, `sleep`, `lpcd`) nennt. Jede andere Zeile bleibt reserviert.“

**L5, Abschnitt 9, „Abfragezyklus der Firmware“ (Zeilen 447 bis 458).** Zusatz: „Ist der Entpreller im Zustand `LEER`, `CFG wach=1` gesetzt und der PN5180 mindestens 4.0, gilt statt des Abfragezyklus der **Wachbetrieb**: PN5180 im LPCD
(Intervall `LPCD_INTERVAL_MS`). Eine Feldänderung beginnt volle Zyklen; nach `LPCD_RUECK_ZYKLEN` Zyklen mit Ergebnis `nichts` in Folge geht der Chip zurück in den LPCD. Der Entpreller sieht nur volle Zyklen. `polls`, `hits`, `errors` und `cycle_ms` zählen nur volle Zyklen.“

**L6, Abschnitt 10, Zeitkonstanten (Zeilen 462 bis 497).** Neu in der Tabelle der Firmware (`timing.h`):

| Name | Wert | Bedeutung |
|---|---|---|
| `LPCD_INTERVAL_MS` | 300 | Abstand der LPCD-Messungen (Aus und Wachbetrieb), Messung 2 |
| `LPCD_ARM_MS` | 2000 | `LEER` so lange, bevor der Wachbetrieb beginnt |
| `LPCD_RUECK_ZYKLEN` | 5 | leere Zyklen bis zurück in den LPCD |
| `LPCD_FALSCH_MAX` | 3 | Fehlmeldungen in 10 s, dann Intervall × 4 und Neuabgleich |
| `PAD_PULS_MS` | 150 | Dauer des Pulses auf Pad 10, Messung 5 |
| `WECK_LAUFLICHT_MAX_S` | 30 | Lauflicht und Warten auf das erste `PING` |
| `VBUS_WEG_ENTPRELL_MS` | 3000 | so lange muss VBUS weg sein, ohne `SLEEP` |
| `SLEEP_WARTEN_S` | 90 | nach `SLEEP` auf das Ende der 5 V warten |
| `RING_TIMEOUT_S` | 15 | ohne `RING`/`PING`: Ring aus |
| `RING_AUS_VERZ_MS` | 1000 | Daten Low, dann MOSFET aus |
| `RING_DECKEL_PROZENT` | 25 | Helligkeitsdeckel (gleich `led.py:29`) |
| `RING_WECK_SICHER` | 5 | Lauflicht-Helligkeit, wenn `wring_s` abgelaufen ist |

Im Box-Dienst (`reader.py`): `RING_KEEPALIVE_S` = 5, `SLEEP_OK_FRIST_S` = 1 (so lange wartet der Pi auf `SLEEP_OK`; danach fährt er trotzdem herunter).

**L7, Abschnitt 12, Verbindungsaufbau (Zeilen 529 bis 551).** Zusatz nach Schritt 4: „5. Hat das `HELLO` `caps`, sendet `reader` `CFG` aus der Konfiguration (`[leser] lpcd`, `wach`) und, wenn `ring` genannt ist, das aktuelle `RING`. Folgt dem `HELLO` eine Zeile `WAKE`, meldet `reader` das Ereignis `LeserWecken(grund, ring)`.“

**L8, Abschnitt 13, Versionsregel (Zeilen 573 bis 591).** Klarstellung: „Neue **Zeilen vom Box-Dienst** an den Leser, die eine ältere Firmware mit `bad_command` beantwortet, brauchen keine neue `proto`, wenn der Box-Dienst sie nur bei passendem `caps` sendet. Die Mindestversion der Firmware regelt `firmware_min`.“

**L9, „Festlegungen in diesem Vertrag“ (ab Zeile 593).** Neu 18 bis 21: (18) `WAKE` kommt einmal je Wecken, spätere `HELLO` tragen keins; (19) `RING` wird alle 5 s wiederholt, der ESP32 startet bei gleichem Muster nichts neu; (20) Pi-Hänger und Schlafen: nur der ESP32 entscheidet, wann er schläft;
(21) Deckel 25 % gilt in der Firmware. **L10:** `reader-v1-examples.txt`: neue Abschnitte mit Zeilen für `HELLO caps=…`, `WAKE`, `SLEEP`/`SLEEP_OK`, `CFG`, `RING` (gültig und ungültig). Die Firmware-Tests lesen die Datei zur Laufzeit (`firmware/tobibox-reader/README.md`, „Tests auf dem Rechner“), die neuen Beispiele werden also sofort Tests.

### 4.5 Bauteile der Firmware (neu)

Reine Logik ohne Arduino-Typen, damit sie in `pio test -e native` läuft (wie `debounce.cpp`): `ring.cpp/h` (Muster-Engine, Helligkeitsstufen), `power_fsm.cpp/h` (Zustände aus 4.1, Zeitregeln, Pad-Puls-Plan),
Erweiterung `protocol.cpp` (neue Zeilen, `caps`). Hardwarenah (Arduino): `hw_ring.cpp` (zweiter SPI-Host mit DMA, **nicht** der des PN5180, sonst stören sich Ring und NFC, Plan 8.4.4), `hw_power.cpp` (Tiefschlaf, EXT1, Pins),
`reader.cpp` (LPCD-Aufruf der Bibliothek).

---

## 5. Hardware-Anforderungen

Nur Anforderungen und offene Messpunkte; kein Schaltplan. Die Nummern H1 bis H8 stehen in der Messliste (Abschnitt 10).

### 5.1 H1: Versorgung des ESP32 und PN5180 aus BAT

*   BAT (PiSugar-Pad 2) liegt bei 3,0 bis 4,2 V (`research.md:15`). Ein Regler auf **3,3 V** mit sehr kleinem Ruhestrom (Ziel ≤ 5 µA) speist ESP32 und PN5180-Logik **dauernd**, auch wenn der Pi läuft.
*   Spitzenstrom ≥ 150 mA (ESP32 im Betrieb, PN5180-Pulse, Ring-Datenleitungen); Unterspannungs-Abschaltung des Reglers bei etwa 3,1 V, damit der ESP32 den Akku nicht unter die Schutzgrenze zieht.
*   **Offen (Messpunkt):** Die PiSugar-Doku nennt weder Belastbarkeit noch Schutzschaltung von Pad 2 (`research.md:217`, Messung 7). Bleibt Pad 2 bei leerem Akku stromführend? Rückfall: eigene Zelle (`research.md:220`), wäre eine Stücklistenänderung.
*   Ruhestrom der SuperMini-Platine: Verkäufer 43 µA, LDO und Power-LED können mehrere 100 µA ziehen (`research.md:79`). Die LED wird entfernt oder getrennt; der Platinen-Regler darf nicht zusätzlich am 3,3-V-Netz hängen (H2).

### 5.2 H2: Trennung von der USB-5-V des Pi, Rückspeisung

*   Der ESP32 hat zwei mögliche Quellen: BAT-Regler und die 5 V des Pi-USB. **Empfehlung:** ESP32 nur aus dem BAT-Regler; das USB-Kabel zum Pi führt **Daten und Masse, aber nicht VBUS** zum ESP32 (Datenkabel ohne VBUS-Ader oder ein Hausmacher-Kabel). Die 5 V des Pi gehen **nur** über einen Spannungsteiler (z. B. 100 kΩ/200 kΩ, Strom nur bei Pi an) an den Eingang `VBUS_SENSE`.
    So gibt es keine zwei Regler am 3,3-V-Netz und keine Rückspeisung in den USB-Port des Pi. Der Pi-3A+-Port hat keinen belegten Schutz gegen Rückspeisung (nicht geprüft).
*   **Offen (Messpunkt, Messung 8):** Enumeriert der ESP32-S3 (USB-Serial/JTAG) am Pi, wenn VBUS nicht anliegt? Rückfall: Ideal-Diode (ODER) aus Pi-5-V und 3,3-V-Pfad, dann fließt kein Strom in den Pi-Port, und der Platinen-Regler muss getrennt werden.
*   `VBUS_SENSE` und der PN5180-IRQ müssen **RTC-fähige** GPIOs sein (ESP32-S3: GPIO 0 bis 21), sonst weckt der Pin nicht aus dem Tiefschlaf (`research.md:207`).

### 5.3 H3: Transistor (Schalter) an Pad 10

*   Verbindet Pad 10 mit BAT. Auswahl nach Gebrauch, nicht nach Teilenummer: **PhotoMOS oder Optokoppler** (unabhängig vom unbekannten Pegel an Pad 10) oder P-FET/PNP mit Treiber-Transistor.
*   Anforderungen: **Sperrstrom ≤ 1 µA** (sonst Ruhestrom und Fehlauslösung), aus bei Reset und Tiefschlaf (Gate/Basis mit Widerstand), Schaltstrom reicht für das, was der Taster zieht (Messung 5: Pegel, Strom, Pull-Widerstand an Pad 10 sind **nicht dokumentiert**, `research.md:188`).
*   Parallel zum Arcade-Hauptknopf (`stueckliste-und-psp.md:48`). Anti-Mistouch aus (4.2).

### 5.4 H4: MOSFET für den Ring

*   **High-Side**, schaltet die 5-V-Versorgung des Rings (hinter dem PTC 1,1 A, `stueckliste-und-psp.md:67-70`), Gate wird vom ESP32 über einen kleinen Treiber-Transistor geschaltet (ein P-FET mit Source an 5 V würde vom 3,3-V-Pegel nicht sicher sperren), Gate-Pull-up: **standardmäßig aus** (Reset, Tiefschlaf).
*   Dauerstrom ≥ 1 A (25 % ≈ 0,6 A, Spitzen bis 2,4 A bei voll weiß, `stueckliste-und-psp.md:67-69`), Rds(on) so klein, dass der Spannungsabfall unter 50 mV bleibt; Einschaltstrom begrenzen (Ring-Kondensatoren).
*   **Der Pegelwandler (74AHCT125, Plan Punkt 6) hängt hinter dem MOSFET**, und der ESP32 legt vor dem Abschalten beide Datenleitungen auf Low. Sonst versorgt der Datenpegel den „stromlosen“ Ring über seine Eingangsdioden (Rückspeisung). **Messpunkt (Messung 9):** Strom des Rings bei offenem MOSFET (Ziel < 10 µA).
*   Einsparung laut Brief und `research.md:116`: 0,14 bis 0,2 W in Bereit [Schätzung für einen LuMini; Messung 9].

### 5.5 H5: Ring-Leitungen vom Pi zum ESP32; freie ESP32-Pins; Folgen für den Pi

*   Daten und Takt des Rings wandern von Pi-GPIO 23 und 24 (`stueckliste-und-psp.md:411-412`) an den ESP32. Der 74AHCT125 bleibt (3,3 V vom ESP32, 5 V zum Ring). Am Pi werden **GPIO 23 und 24 frei** (Plan Teil 2: „Frei: GPIO 7, 12, 13, 16“ wird zu „… 7, 12, 13, 16, 23, 24“); sonst ändert sich nichts an der Pi-Belegung. Die Pi-Seite sendet keinen Bit-Bang mehr (Plan 5.5.1 entfällt, ersetzt durch `RING`-Befehle).
*   ESP32-Pins heute belegt: GPIO 8 (RST), 9 (BUSY), 10 (NSS), 11 (MOSI), 12 (SCK), 13 (MISO) (`config.example.h:9-14`). Neu gebraucht:

    | Funktion | Vorschlag | Bedingung |
    |---|---|---|
    | PN5180-IRQ | GPIO 4 | RTC-fähig, kein Strapping-Pin |
    | `VBUS_SENSE` (5 V des Pi, Teiler) | GPIO 5 | RTC-fähig, Weckquelle |
    | Pad-10-Schalter | GPIO 6 | beim Reset aus |
    | Ring-MOSFET (über Treiber) | GPIO 7 | beim Reset aus |
    | Ring Daten / Takt | GPIO 1 / GPIO 2 | zweiter SPI-Host |
    | `STROM_IN` (optional, Teiler am Ladeeingang) | frei | RTC-fähig |
    | Akku-Spannung (ADC, optional) | frei | ADC-fähig |

    GPIO 1 bis 7 sind frei (sieben Stück); 0, 3, 45, 46 sind Strapping-Pins und werden vermieden. Welche Pins der **SuperMini** herausführt, ist hier nicht geprüft (am Muster nachzählen); fehlen Pins, entfallen `STROM_IN` und ADC zuerst.

### 5.6 H6 bis H8: Optionen mit Messung

*   **H6 `STROM_IN`:** Teiler vom Ladeeingang des PiSugar an den ESP32. Damit weckt der **ESP32** bei steigender Flanke (Variante B), unabhängig von „Einschalten bei Strom“ des PiSugar (E4: Flanke oder Pegel unbekannt, `research.md:183`). Kostet zwei Widerstände, spart die Boot-Schleife (Hauptknopf lang am Sockel startet nicht neu) und liefert den Weckgrund `strom`.
*   **H7 Hauptknopf mitlesen:** Teiler an Pad 10 meldet dem ESP32 jeden Tastendruck, er sendet ihn als Zeile an den Pi und löst damit B2 (`taste_befehl` unbelegt, `box-software.md:552-557`). **Nicht** Teil dieses Entwurfs, nur als Option notiert (E11).
*   **H8 Akku-Spannung (ADC):** damit der ESP32 den Pi bei fast leerem Akku nicht weckt. Ersatz: `CFG lpcd=0` bei Tiefstand (Z08).

---

## 6. Schneller Start

### 6.1 Ziele

| Messpunkt | Ziel | Grundlage |
|---|---|---|
| Auflegen (Aus) → Lauflicht | ≤ 1,5 s | LPCD 0,3 s + Aufwachen + Lesung + Puls + 5 V [Schätzung, Abschnitt 6.2] |
| 5 V am Pi → Frühton | ≤ 5 s | Firmware 1,25 s + Kernel ≈ 2 s + Frühdienst ≈ 1,5 s [Schätzung] |
| 5 V am Pi → `Bereit` | ≤ 8,5 s | siehe unten |
| Auflegen (Aus) → erster Ton des Hörspiels | **≤ 10 s** (Brief) | 1,0 s Wecken + 8,5 s + 0,5 s |
| Auflegen (Bereit) → Hörspiel | ≤ 3 s (Ziel 1,5 s) | Abschnitt 4.3 |

**Ehrliche Einordnung:** Belegt sind nur Fremdwerte: Pi 3 mit getrimmtem Buster 1,79 s Kernel + 5,78 s Userspace = 7,57 s ohne Firmwarezeit (P20), Firmware 1,25 s (P22, `research.md:145, 150`). Box-Dienst und MPD kommen oben drauf.
Für den Pi 3A+ mit Raspberry Pi OS Lite gibt es keine Messung (`research.md:139`). Die 10 s sind **ehrgeizig**; fällt Messung 1 schlechter aus, ist der Rückfall 15 s (E13).

### 6.2 Zeitleiste Wecken durch Tobie [Schätzung, Messung 10]

| Schritt | Zeit | Summe |
|---|---|---|
| Tobie aufgelegt → LPCD-Meldung | 0 bis 0,3 s (Mittel 0,15) | 0,15 bis 0,3 |
| ESP32 wacht auf, PN5180 starten, eine Lesung | ≈ 0,3 s | ≈ 0,6 |
| Pad-10-Puls, PiSugar schaltet 5 V ein | 0,15 + ≈ 0,2 s | ≈ 0,95 |
| Lauflicht (MOSFET an, erster Rahmen) | < 0,05 s | **≈ 1,0 bis 1,3** |

### 6.3 Arbeitspaket Boot-Kürzung (Pi, Hebel mit Beleg zuerst)

Reihenfolge: **messen** (`systemd-analyze`, `blame`, `critical-chain`, dazu Stoppuhr per ESP32: Lauflicht bis Ton), dann **einzeln** ändern und neu messen. Jede Maßnahme steht mit ihrem Beleg; ohne Beleg ist sie nur ein Versuch.

| # | Maßnahme | Beleg |
|---|---|---|
| 1 | `cloud-init` abschalten (`/etc/cloud/cloud-init.disabled`), falls im Image | P33: >1 min Hänger auf Trixie/Zero (`research.md:157`) |
| 2 | `NetworkManager-wait-online` nicht abwarten (maskieren); Box-Dienst hängt **nicht** an `network-online.target`. Heute wartet `Bereit` nur auf MPD (`app.py:919`), nur der Start-Sync wartet bis 30 s auf das Netz (`NETZ_KLASSE_WARTEN_S`, `core-interface.md:1349`) | P21: 7,4 s im Beispiel (`research.md:146, 158`) |
| 3 | Bluetooth und `hciuart` aus (`dtoverlay=disable-bt`) | P20: 13 Dienste; P31: −4 s; hciuart 9 s (`research.md:149, 157`) |
| 4 | Unnötige Dienste und Timer aus: `man-db`, `logrotate` beim Start, `apt-daily*`, `avahi`, `rsyslog`, `dphys-swapfile`, `keyboard-setup`, `triggerhappy`, `ModemManager`, `exim4` | P20, P21: `logrotate` 6,2 s, `man-db` 15 s (`research.md:146, 157`) |
| 5 | `quiet`, `loglevel=3`, `boot_delay=0`, `disable_splash=1`, keine Konsole auf tty1 | **Suchtreffer ohne Messung** (`research.md:159`): erst messen |
| 6 | `gpu_mem=16` und `start_cd.elf` | P22: −0,5 s im Buildroot-Beispiel; hier nur Versuch (`research.md:150`) |
| 7 | `tobiboxd` und MPD parallel starten, nicht nach `multi-user`; Python: `.pyc` vorkompiliert (im Installer), schwere Importe verzögert (`python -X importtime`); MPD mit fertiger Datenbank, `auto_update no` | Eigenmessung nötig (kein Beleg) |
| 8 | WLAN darf `Bereit` nicht aufhalten: NetworkManager verbindet nach `Bereit`; die erste Netz-Klasse kommt später | `app.py:919-925`: `Bereit` hängt heute nicht am Netz |
| 9 | `reader` öffnet den ESP32 sofort (er läuft schon); kein Warten auf den ESP32-Start (spart 1 bis 2 s Schätzung, `research.md:161`) | `app.py:924-927`: Leser startet nach `Bereit` |
| 10 | SD-Karte: Klasse A1/A2, `noatime` (steht schon in AP P.1) | keine Quelle zur SD-Karte (`research.md:159`): messen |

Abbruchkriterium: Nach Maßnahme 1 bis 4 und 7 keine 8,5 s bis `Bereit`, dann E13 (Ziel 15 s). Kein Wechsel auf ein Eigenbau-Image (Buildroot, P22) in diesem Entwurf.

### 6.4 Früher Start-Ton und „ein Ton, nicht zwei“

*   **Wer:** ein eigener systemd-Dienst `tobibox-fruehton.service` (`deploy/pi/`, Typ `oneshot`, `DefaultDependencies=no`, `After=sound.target`, `Before=tobiboxd.service`). Er spielt `box/sounds/start.wav` über das `softvol`-Gerät für Töne (Entscheidung J5, `box-software.md:446`).
    Er braucht weder MPD noch den Box-Dienst und weder Netz noch ESP32.
*   **Wann:** nur im Modus `normal` bei sicherer Uhr. Er liest die PiSugar-RTC (I²C, ohne `pisugar-server`) und die Leise-Zeiten aus `config.json` und benutzt dieselbe Funktion wie der Kern (`quiet.wirkung_jetzt`, `quiet.py:104`).
    Unter „leiser“, „stumm“ und bei unsicherer Uhr bleibt er still (Ton `start` und Andocken nachts: S5). **Offen (Messung 11):** wie lange der Python-Start auf dem Pi 3A+ dauert; zu lange ⇒ kleiner Shell-Dienst mit einer vorberechneten Datei, die der Box-Dienst beim Beenden schreibt.
*   **Pegel:** wie `hinweis` (nach dem Einschalten gilt `lautstaerke_start`, nicht die Abendlautstärke; die Begründung steht schon im ruhenden Entwurf, C10).
*   **Abstimmung mit dem Box-Dienst:** Der Frühdienst schreibt `/run/tobibox/fruehton.json` (`{"boot_id": …, "ton": "start"|"keiner"}`, tmpfs: gelöscht bei jedem Einschalten). Der Box-Dienst liest und **löscht** die Datei beim Start; ist die `boot_id` gleich der aktuellen
    und die Datei da, gibt `app` `Bereit(fruehton=True)` aus, und `session._bereit` (`session.py:844-845`) spielt **keinen** `start`-Ton. Nach einem Dienst-Neustart fehlt die Datei: `start` klingt wie bisher (Entscheidung G).
    Der Ton `lader` spielt nur bei einem **Wechsel** nach `Bereit` („kein Strom“ → „Strom“), nie bei der ersten Messung. So kommt weder `start` zweimal noch `start` und `lader` zusammen.
*   **Lauflicht-Übergabe:** Hat `LeserWecken` `ring=1`, spielt `led.py` bei `Bereit` **kein** eigenes Lauflicht (`led.py:233-234`) und sendet gleich den Zustand danach; das beendet das Lauflicht des ESP32. Bei Dienst-Neustart (kein `WAKE`) bleibt `led.py` wie heute.

---

## 7. Budget ohne Sockel, typischer Tag [Schätzung]

Grundlage: 15 Wh nutzbar (`stueckliste-und-psp.md:335-338` nach `research.md:7`); Leistungen aus `research.md` (1.6, 1.4, 1.3) und Brief. Tagesbild wie im Brief: 4 h Hören, 10 Pausen, der Rest Aus; jede Nacht am Sockel.

| Posten | Rechnung | Wh |
|---|---|---|
| Hören | 4 h × 1,6 bis 1,9 W | 6,4 bis 7,6 |
| 10 Pausen mit je 10 min Bereit | 100 min × 1,0 bis 1,3 W | 1,7 bis 2,2 |
| 3 Starts aus Aus | 3 × (25 s × 1,5 W) | 0,03 |
| Aus (16 h): PiSugar ≤ 1 mA, Wächter 0,2 bis 0,8 mA | 0,2 bis 1,8 mA × 3,7 V × 16 h | 0,01 bis 0,11 |
| **Summe** | | **8,1 bis 9,9** |
| Reserve | 15 − Summe | 5,1 bis 6,9 (≈ 3 bis 4 h Hören) |

*   Schlechtester Fall: Bereit bei 1,75 W (Gegenrechnung mit Ring unter Strom, `research.md:114`): Summe bis 10,7 Wh. Auch dann bleiben rund 4 Wh.
*   **Wozu die Frist:** Bereit den ganzen Tag (16 h × 1,0 bis 1,3 W = 16 bis 21 Wh) leert den Akku. Eine Pause von 10 min kostet 0,17 bis 0,22 Wh (rund 1,3 % des Akkus), ein Kaltstart nur 0,01 Wh (`research.md:120`):
    Die 10 min sind eine Entscheidung für Komfort (Hörspiel in unter 3 s), nicht für Energie.
*   **Unsicher:** Ruhestrom des PiSugar im Hibernate (keine Zahl, `research.md:62`), Strom von BAT-Regler, Pad-Schalter und MOSFET im Aus, LPCD-Mittelwert bei 300 ms (ESPuino nennt +300 µA bei 1 s Intervall, `research.md:84`; bei 300 ms mehr).
    Alle Zahlen kommen aus den Messungen 3 und 4 (Abschnitt 10).
*   **Selbstentladung** bei Wochen im Schrank: egal (Brief), aber ein Tiefstand-Aus hält `lpcd=0`, damit ein leerer Akku nicht wieder geweckt wird.

---

## 8. Folgen für Verträge und Design

### 8.1 Verträge: 26 Stellen (19 inhaltlich, 7 Klarstellungen)

Zeilenangaben sind der Stand des Repos am 10.11. Die Wortlaute der wichtigsten Stellen stehen in 8.2 bzw. 4.4 (L1 bis L10).

| # | Datei | Abschnitt (Zeile) | Art | Änderung |
|---|---|---|---|---|
| V1 | `reader-v1.md` | 3 Zeilentabelle und Felder (72-109) | inhaltlich | `WAKE`, `SLEEP_OK`, `HELLO.caps` (L1) |
| V2 | `reader-v1.md` | 3 „Alle Felder … Pflicht“ (81) | Klarstellung | optionales Feld (L2) |
| V3 | `reader-v1.md` | 7 Fehlercodes (231-252) | inhaltlich | vier neue Codes (L3) |
| V4 | `reader-v1.md` | 8 Zeilen zum Leser (281-297) | inhaltlich | `RING`, `SLEEP`, `CFG` (L4) |
| V5 | `reader-v1.md` | 9 Abfragezyklus (447-458) | inhaltlich | LPCD-Wachbetrieb (L5) |
| V6 | `reader-v1.md` | 10 Zeitkonstanten (460-497) | inhaltlich | 12 Firmware-, 2 Dienst-Konstanten (L6) |
| V7 | `reader-v1.md` | 12 Verbindungsaufbau (529-551) | inhaltlich | `CFG`, `RING`, `WAKE` nach dem `HELLO` (L7) |
| V8 | `reader-v1.md` | 13 Versionsregel (573-591) | Klarstellung | Befehle ohne neue `proto`; `fw` 2.0.0 (L8) |
| V9 | `reader-v1.md` | Festlegungen (593-666) | inhaltlich | Nr. 18 bis 21 (L9) |
| V10 | `reader-v1-examples.txt` | neue Abschnitte | inhaltlich | Beispielzeilen, Testgrundlage der Firmware (L10) |
| V11 | `core-interface.md` | 3.1 `LeserHallo` (128), neues Ereignis | inhaltlich | `caps: str`; neu `LeserWecken(grund, ring)` |
| V12 | `core-interface.md` | 3.3 `Bereit` (194) | inhaltlich | `fruehton: bool = False` (Wortlaut unten) |
| V13 | `core-interface.md` | 3.6 `LaderGeaendert` (227) | Klarstellung | Bedeutung „Strom am Eingang, jede Quelle“ |
| V14 | `core-interface.md` | 3.6 `SyncAbgebrochen` (234) | Klarstellung | Satz „keine Wiederholung am Lader“ bzw. Wiederholung streichen |
| V15 | `core-interface.md` | 4 `TonSpielen` (316) | inhaltlich | neuer Ton `lader` |
| V16 | `core-interface.md` | 5.2 Zeile `idle.py` (359) | inhaltlich | Ausgang `TonSpielen` (auch `lader`); Zustand „Frist ohne Strom“ |
| V17 | `core-interface.md` | 6.2 Konfliktregeln (468-470) | inhaltlich | Regel 2a: `lader` entfällt unter „leiser“, „stumm“, bei unsicherer Uhr |
| V18 | `core-interface.md` | 8.1 Töne (851-858) | inhaltlich | Pegel von `lader` wie `hinweis` |
| V19 | `core-interface.md` | 9 Punkt 9, Leerlauf/Start am Lader (1123-1152) | inhaltlich | 10 min ohne Strom, keine Frist mit Strom, Andocken, Wiederholung entfällt (Wortlaut unten) |
| V20 | `core-interface.md` | 6.5 und 10 (643, 1296-1320) | Klarstellung | `app`: `SLEEP` vor dem Poweroff; `led` gibt `RING` an `reader` |
| V21 | `core-interface.md` | 11 Konstanten (1344-1353) | inhaltlich | `LEERLAUF_S` 600; `START_WIEDERHOLUNG*` entfallen; `LADER_SPERRE_S` = 10 |
| V22 | `mqtt-v1.md` | 3.3 Feld `lader` (156), 6.2 Entität (601) | Klarstellung | „Strom am Eingang, jede Quelle“ |
| V23 | `mqtt-v1.md` | 3.4 `fehler`, Codes der Box (220) | inhaltlich | `baustein="leser"`, `code="schlafen_abgebrochen"` (aus `ERR sleep_aborted`) |
| V24 | `ha-websocket-v1.md` | `tobibox/box/sync` (940-950), Update-Bedingung | Klarstellung | „Lader“ = jede Quelle; der automatische Sync beim Andocken folgt der Netz-Regel (S7, S8) |
| V25 | `data-model.md` | 1.6 Dateien (134, 150-154) | inhaltlich | neue flüchtige Datei `/run/tobibox/fruehton.json` |
| V26 | `data-model.md` | 2 `hinweis_pegel` (208), Töne | inhaltlich | `lader.wav`, Pegelregel; Pegel des Frühtons |

Nicht nötig (anders als im ruhenden Entwurf): `Bereit.einschalten`, `ende.json`, `update_vormerken` (ha-websocket Befehl 37), `update_vorgemerkt`, Schleifen-Fehlercode, Regel 1a, Konstanten `LADER_KURZ_S`, `LADER_RUECKMELDUNG_S`, `LADER_NACHLAUF_S`, `SCHLEIFE_S`, `STROM_START_WARTEN_S`.

### 8.2 Wortlaut der wichtigsten Stellen

**V12 `Bereit`** (`core-interface.md:194`). alt: Felder „–“; „Bei `Bereit` spielt der Kern den Start-Ton (CUJ 20 …)“. Neu: Felder `fruehton: bool = False`;
„… Hat der Frühdienst `tobibox-fruehton` für diesen Start entschieden (Datei `/run/tobibox/fruehton.json` mit der aktuellen `boot_id`, `data-model.md` 1.6), setzt `app` `fruehton = True`; dann spielt `session` **keinen** Ton `start`
(der Frühdienst hat ihn gespielt oder bewusst unterlassen). Sonst und nach einem Dienst-Neustart spielt der Kern den Start-Ton wie bisher.“ Der Vorgabewert `False` lässt jeden bestehenden Aufruf von `Bereit()` unverändert.

**V11 `LeserHallo` / `LeserWecken`** (`core-interface.md:128`). alt: Felder `proto fw build pn5180`. Neu: dazu `caps: str = ""` (Liste der Merkmale, leer bei Firmware 1.x). Neues Ereignis in 3.1:
`LeserWecken(grund: Literal["tobie","strom","extern","reset"], ring: bool)` — Quelle `reader`, „Der Leser meldet, warum er den Pi geweckt hat; `ring` heißt: das Lauflicht des ESP32 läuft noch. Empfänger: `led` (kein eigenes Lauflicht bei `Bereit`), Protokoll. Der Kern ignoriert es.“

**V19 Punkt 9, Leerlauf** (`core-interface.md:1123-1152`). Der Absatz „Start am Lader (09.11., AP 4.8) … Wiederholung alle 10 min …“ **entfällt**. Der Absatz „Leerlauf zählt auch mit liegendem Tobie“ bekommt: „Der Zähler zählt nur, wenn **kein Strom** am Eingang liegt
(`am_lader` ist `False` oder `None`). Mit Strom ist die Abschaltung nie fällig. Kommt der Strom, wird die Frist verworfen; geht er, beginnt sie mit `LEERLAUF_S` (600 s) neu. Ein Wechsel von ‚kein Strom‘ nach ‚Strom‘ **nach** `Bereit` löst, wenn die
letzte Rückmeldung mindestens `LADER_SPERRE_S` zurückliegt, `TonSpielen("lader")` aus (nicht bei Lernmodus, nicht bei laufendem Hörspiel) und `SyncStarten("start_lader")` (einmal je Andocken; die Netz-Regel von `sync` entscheidet). Die erste Messung nach dem Start löst nur den
Sync-Check aus, keinen Ton.“

**V21 Konstanten.** `LEERLAUF_S`: 1200 → **600** („Frist ohne Strom“). Neu `LADER_SPERRE_S` = 10 (`idle.py`: Rückmeldung und Sync-Prüfung beim Andocken). Streichen: `START_WIEDERHOLUNG_S`, `START_WIEDERHOLUNGEN`.

**V25 `data-model.md`** (1.6): „`/run/tobibox/fruehton.json` — flüchtig (tmpfs), Schreiber `tobibox-fruehton`, Leser und Löscher `app` beim Start. `{"boot_id": <Kennung des Starts>, "ton": "start"|"keiner"}`. Nicht im Zustandsverzeichnis, nicht im Sync, kein `schema_version`.“

**Tabelle „Strom / Leerlauf“** (`box-software.md:1383-1394`, ersetzt): Zustände `aktiv`, `leerlauf`, `herunterfahren`.

| Zustand | Ereignis | Befehl | neuer Zustand |
|---|---|---|---|
| `aktiv` | keine Wiedergabe (liegender Tobie zählt nicht, O) | Zähler `LEERLAUF_S` (600 s) starten | `leerlauf` |
| `leerlauf` | Wiedergabe → Zähler verwerfen; Bedienung → Zähler neu | wie bisher | `aktiv` / `leerlauf` |
| `leerlauf` | Strom kommt | Zähler verwerfen („fällig“ nie wahr); Ton `lader`, Sync-Prüfung (Sperre 10 s) | `leerlauf` |
| `leerlauf` | Strom geht | Zähler neu (`LEERLAUF_S` ab jetzt) | `leerlauf` |
| `leerlauf` | Zähler um, **kein Strom**, Sync, Update, Lernmodus laufen | warten; nach dem Ende sofort prüfen (Lernmodus: Zähler neu) | `leerlauf` |
| `leerlauf` | Zähler um, **kein Strom**, nichts läuft | Zeiger speichern, `SLEEP`, Herunterfahren | `herunterfahren` |
| `aktiv`, `leerlauf` | Hauptknopf lang | Zeiger speichern, `SLEEP`, Herunterfahren | `herunterfahren` |
| `aktiv`, `leerlauf` | Tiefstand (kein Strom) | Sync abbrechen, Ton `akku_leer`, `CFG lpcd=0`, `SLEEP`, Herunterfahren | `herunterfahren` |
| `herunterfahren` | Kommando hat nicht gewirkt (B1) | Protokoll, Hinweis an HA, Zähler neu | `aktiv`, dann `leerlauf` |
| beim Start | `Bereit`, Strom bekannt und vorhanden | einmal Sync prüfen (kein Ton, kein Kurz-Modus) | wie oben |

### 8.3 Was aus S1 bis S11 und dem Entwurf „Start am Lader“ gilt

| Eintrag | Schicksal | Begründung |
|---|---|---|
| R8 Andocken weckt | **gilt** | Z03, CUJ 25 |
| R10 eine Buchse | **gilt** | `battery_power_plugged` an der einzigen Buchse: Messung 14 |
| S1 jeder Start mit Strom ist ein Start am Lader | **gilt, vereinfacht** | Kein Merker; Andocken-Sync nach `Bereit`. Kein `einschalten`-Feld nötig: Ein Sync-Check beim Dienst-Neustart ist harmlos |
| S2 Kurz-Zähler 120 s | **entfällt** | Am Sockel bleibt die Box bereit (CUJ 23) |
| S3 was den Kurz-Modus beendet | **entfällt** | kein Kurz-Modus |
| S4 liegender Tobie spielt beim Start | **gilt** | CUJ 20/22. Nachts schützt „stumm“; „leiser“ spielt (E5 und G2 des Reviews: ein Stromstoß nachts trifft nur eine Box im Aus; am Sockel läuft sie ohnehin) |
| S5 Leise-Zeiten | **gilt, erweitert** | 3.5; Frühton und `lader` nur im Modus „normal“ bei sicherer Uhr; Lauflicht des ESP32 über `wring` |
| S6 Update vormerken | **entfällt** | Am Sockel ist die Box immer an; HA schickt `update` jederzeit. Spart `update_vormerken`, `update_vorgemerkt`, Konstante `LADER_NACHLAUF_S`, H1 bis H3 des ruhenden Entwurfs |
| S7 Start-Sync auch über Hotspot | **gilt** | `syncregel.py` unverändert (Hotspot mit Strom oder Akku > 50 %); Folge für Auto und Powerbank bleibt (E1) |
| S8 Andocken bei laufender Box prüft den Sync | **gilt** | Z15, einmal je Andocken, Sperre 10 s |
| S9 spielendes Hörspiel: nur Ring | **gilt** | Z09 |
| S10 Sockel und Kabel nicht unterscheiden | **gilt** | `STROM_IN` (H6) ändert daran nichts |
| S11 Frühstart-Ring erst messen | **erledigt durch E7** | Lauflicht auf dem ESP32; der „kleine Frühstart-Dienst“ des Ring-Treibers entfällt |
| Q1 Wiederholung im Heimnetz | **gegenstandslos** | Wiederholung entfällt; das Netz kommt später: `sync.setze_netz` startet sofort (laut ruhendem Entwurf `sync.py:176-177`, dort geprüft) |
| Q3, Q4 | **gegenstandslos** | kein Kurz-Modus |
| Boot-ID (G), `lauf.json` | **gilt unverändert** | Entscheidung G braucht keine neue Datei; `lauf.json` wird weiter nur mit dem Tobie geschrieben |
| Schleifenbremse, `ende.json` | **entfällt** | Am Sockel gibt es keinen automatischen Abschalt-Zyklus mehr. Bleibt: Hauptknopf lang am Sockel (E4) |
| „erste Messung vor `Bereit`“ (3.3) | **entfällt** | Der Frühdienst entscheidet über den Start-Ton allein; `Power.start` liefert Zeit vor Lader vor Akku (`power.py:263-267`), das genügt dem Ring |
| `Bereit.einschalten`, Regel 1a | **entfällt** | `fruehton` ersetzt beides |
| Entprellen (10 s), Ring-Entprellen | **gilt, übernommen** | Z15; 3.6 |
| Helligkeit 15/5/3 %, Stufe ≥ 1, Faktor-Ausnahme | **gilt, übernommen** | 3.5, in der Firmware |
| Ton `lader` mit Pegel `hinweis` | **gilt, übernommen** | V15, V17, V18, V26 |

### 8.4 Design, Plan, Betrieb, Code (kurz)

| Datei | Stelle | Art |
|---|---|---|
| `box-software.md` | CUJ 10 (789), 15 (837), 16 (855), 18 (881), 20 (919); neue CUJ 21 bis 25 nach 934 | inhaltlich |
| `box-software.md` | Entscheidung O (532-537), B2 (552-557); neu Entscheidungen zum Ein-/Ausschalten | Klarstellung |
| `box-software.md` | Baustein 1 Firmware (967-1083), Zeitbudget (1043), Baustein 2 Protokoll (1084-1117) | inhaltlich |
| `box-software.md` | Tabelle „Strom / Leerlauf“ (1380-1397), Konflikte (1399-1416), Netz/Sync/Strom (1692-1738), Update (1740) | inhaltlich |
| `box-software.md` | Risiken (621ff.), AP 4.1 (2784), AP 4.3 (2815), neue Arbeitspakete (Abschnitt 10) | inhaltlich |
| `docs/plan/stueckliste-und-psp.md` | 1.5 Laufzeit (374-385), Teil 2 Pinbelegung (389-421), Stückliste (Regler, Schalter, MOSFET), 3.1.3, 5.5.1/5.5.2, 5.6.3/5.6.5/5.6.8, 5.7, 8.2.4, Punkt 3, Entscheidungsliste (734-738) | inhaltlich |
| `docs/betrieb/pisugar-wecker.md` | Abschnitt 4 und 6 (Wecker, Start-Sync-Lücke) | inhaltlich |
| `docs/betrieb/mac-prototyp.md` | Zeile 1730 (Probe „Start-Sync am Lader und Wiederholung“) | Klarstellung |
| `docs/timing.md` | zwei Zeilen: Bereit mit LPCD, Aus → Hörspiel | inhaltlich |
| `firmware/tobibox-reader/README.md`, `config.example.h` | Pins, Tests | inhaltlich |
| Code | `idle.py` (Frist ohne Strom, Andocken, Wiederholung entfernt), `led.py` (Muster-Beschreibung, Bereit dunkel, Helligkeit), neu `ringsender.py`, `reader.py` (neue Zeilen), `power.py` (Anti-Mistouch, `CFG lpcd` bei Tiefstand), `app.py` (`SLEEP` vor Poweroff, `fruehton`), `session.py:844-845`, `core.py:44, 119`, `config.py` (`[leser] lpcd, wach`), neu `fruehton.py`, `deploy/pi/` | Code |

---

## 9. Offene Fragen für Tobias

E1 und E2 sind entschieden (Brief). E7 ist entschieden. Hier E3 bis E6 und neue Fragen.

| # | Frage | Empfehlung |
|---|---|---|
| **E3** | Akku am Sockel dauernd bei 100 %: hinnehmen? | Am Muster prüfen, ob der PiSugar eine Ladegrenze kann (Messung 6); sonst hinnehmen, der Akku ist ein Verschleißteil. Wirkt nur am Sockel |
| **E4** | „Einschalten bei Strom“ ab Werk **an**: Hauptknopf lang am Sockel startet die Box sofort neu? | Messen (Messung 6). Startet sie neu, hinnehmen: am Sockel ist „bereit“ gewollt. Sonst (Flanke) ist es unkritisch. Zeigt sich ein Zyklus, wird `STROM_IN` (H6) gebaut und „Einschalten bei Strom“ aus. Eine Schleifenbremse ist nicht nötig, solange am Sockel nichts von selbst abschaltet |
| **E5** | Tobie weckt die Box nachts unter „stumm“? | Keine Sonderregel: Die Box startet, zeigt nichts (Lauflicht aus), bleibt in `gehalten` (Hinweis leise nach CUJ 15), ist nach 10 min wieder aus. Am Sockel läuft sie ohnehin |
| **E6** | Ring in Bereit? | Dunkel (stromlos). Aufleuchten: 3 s nach Bedienung, Auflegen, Abheben; 5 s Akku bei Andocken und Abziehen; 10 s Pause nach dem Spielen bei liegendem Tobie; Lernmodus dauernd (Abschnitt 1.3). Ändert die Entscheidung O für den Ring („Pause bleibt sichtbar“) nur in Bereit nach 10 s |
| **E8** (neu) | Ton beim Andocken: eigener Ton `lader`, oder reicht der Start-Ton? | `lader` (neue Datei) **nur** für Andocken bei laufender Box in Bereit; beim Andocken aus Aus gilt der Frühton `start`. Beide nicht unter „leiser“ und „stumm“. Billiger wäre `hinweis` ohne neuen Ton, aber dann kann die Leise-Regel ihn nicht unterdrücken (sie sieht nur den Namen) |
| **E9** (neu) | Frist beim Abziehen: ab Abziehen oder ab dem letzten Spielen? | **Ab Abziehen** (10 min). Sonst ginge die Box nach einer Nacht am Sockel beim Hochnehmen sofort aus |
| **E10** (neu) | Pi startet, kommt aber nicht hoch (kein `PING` binnen 30 s): soll der ESP32 den PiSugar nach 120 s ausschalten (langer Druck Pad 10) und Tobie-Wecken sperren? | Ja, einmal je Wecken: verhindert leere Akkus durch einen hängenden Pi. Kostet einen Langdruck-Pfad und eine Zeit, die kein Pi-Start überschreiten darf (fsck!). Sonst nur Ring aus + HA-Hinweis |
| **E11** (neu) | Hauptknopf mitlesen (H7), um B2 zu lösen? | Nicht in diesem Paket; nur den Teiler am Platinen-Entwurf vorsehen |
| **E12** (neu) | Rückfall, wenn LPCD durch den Deckel nicht trägt (Messung 2)? | Tobie weckt nicht; Knopf und Strom wecken weiter (CUJ 21 ohne CUJ 22). Der Rest des Konzepts bleibt. Tobias entscheidet nach der Messung, nicht vorher |
| **E13** (neu) | Ziel 10 s bis zum Hörspiel, Rückfall 15 s? | Ziel 10 s, Rückfall 15 s, wenn nach Maßnahme 1 bis 4 und 7 weniger nicht erreichbar ist. Entscheidung nach Messung 1 |
| **E14** (neu) | Frühton nur im Modus „normal“ (kein Ton unter „leiser“, „stumm“, bei unsicherer Uhr)? | Ja. Vereinfacht den Frühdienst und erfüllt S5. Verlust: Unter „leiser“ gab es bisher einen leisen Start-Ton (`core.py:44`: nur „stumm“ ersetzt ihn) |

---

## 10. Arbeitspakete

Neue Nummern **EA0 bis EA14** (Nachtrag zum Umsetzungsplan, `box-software.md` ab 1955). Modelle nach `CLAUDE.md`: Sonnet für Code und Firmware, Haiku für Doku und Boilerplate.

### 10.1 Am Mac und in der Simulation

| AP | Modell | Inhalt | Abhängig von |
|---|---|---|---|
| **EA0** | Sonnet | Verträge V1 bis V26 einarbeiten (Wortlaut aus 4.4 und 8.2); danach Gegenlesen durch einen Goldfisch | Freigabe von Tobias |
| **EA1** | Sonnet | Firmware-Logik nativ: `ring.cpp/h` (Muster, Stufen, Deckel), `power_fsm.cpp/h` (Zustände 4.1, Zeitregeln), `protocol.cpp` (`RING`, `SLEEP`, `CFG`, `WAKE`, `caps`); `pio test -e native` mit neuen Beispielen (V10); Gleichheitstest gegen Prüfbilder aus `led.py` | EA0 |
| **EA2** | Sonnet | `idle.py` + `test_idle.py`: Frist 600 s nur ohne Strom, Strom verwirft, Abziehen beginnt neu, Andocken (Ton, Sync, Sperre), Wiederholung entfernt (Tests Zeilen 505-575 des ruhenden Entwurfs entfallen) | EA0 |
| **EA3** | Sonnet | `led.py` + neu `ringsender.py`: Zustand → `RING`-Befehl, Keepalive, Bereit dunkel, Helligkeit nach 3.5, Entprellen, Prüfbilder (JSON) exportieren; `test_led.py` | EA0 |
| **EA4** | Sonnet | `reader.py` (neue Zeilen, `caps`, `LeserWecken`), `app.py` (`SLEEP` vor Poweroff, `CFG`, `fruehton`), `power.py` (Anti-Mistouch, `CFG lpcd=0` bei Tiefstand), `session.py:844-845`, `config.py`; Sim-Leser (`tobibox sim`) um `WAKE`, `SLEEP_OK` erweitern | EA0, EA1 (Beispiele) |
| **EA5** | Sonnet | `fruehton.py` (`quiet.wirkung_jetzt`, Marke `/run/tobibox/fruehton.json`), `deploy/pi/tobibox-fruehton.service`, Test mit simulierter Uhr | EA0 |
| **EA6** | Haiku | Ton `lader.wav` (`tools/make_sounds.py`, Lautheit −18 LUFS, `lautheit.json`), `core.py` Regel 2a, `sounds.pegel` | EA0 |
| **EA7** | Haiku | CUJ-Tests 16, 21 bis 25 aus den Tabellen 1.2 und 2.1 (Simulation: `box.sende`/`warte`, simulierte Uhr) | EA2 bis EA5 |
| **EA8** | Haiku | Doku nachziehen (Abschnitt 8.4) | EA7 |
| **EA9** | Haiku | Messskript Bootzeit (`systemd-analyze`, Zeitmarken, Auswertung) und Prüfliste zu Abschnitt 10.3 | – |

### 10.2 Am Breadboard oder Muster (Tobias; Sonnet liefert die Messfirmware)

| AP | Wer | Inhalt | Entscheidet |
|---|---|---|---|
| **EA10** | Tobias, Sonnet | Messfirmware `lpcd_probe` (PN5180 LPCD, IRQ-Pin, Tiefschlaf): Tobie durch den Deckel, Schwelle, Intervall, Fehlweckungen, Strom | E12, Messung 2 |
| **EA11** | Tobias | PiSugar: Pad 10 mit Schalter und ESP32 pulsen, Anti-Mistouch, „Einschalten bei Strom“ (Flanke/Pegel), Pad 2 als Quelle, Ruhestrom Aus | E3, E4, H1 bis H3 |
| **EA12** | Tobias, Sonnet | Hardware-Firmware: `hw_power.cpp`, `hw_ring.cpp`, Pin-Belegung, Ring + MOSFET, Aufbau H1 bis H5 | EA1, EA10, EA11 |
| **EA13** | Tobias, Sonnet | Boot-Kürzung am Pi 3A+ (Abschnitt 6.3) mit EA9; Frühdienst messen; Ziel 8,5 s | E13 |
| **EA14** | Tobias | Gesamtprobelauf: Tagesverlauf, Powerbank, Auto, Nacht (Ring-Helligkeit), Akku-Budget (Abschnitt 7) | Abnahme |

**Reihenfolge:** EA10, EA11 und EA13 sofort und parallel zu EA0 bis EA6 (sie können die Annahmen kippen: LPCD trägt nicht, Pad 2 nicht belastbar, Boot-Zeit). Dann EA0, danach EA1 bis EA6 parallel (EA1 und EA4 teilen Beispiele),
EA7, EA8; EA12 nach EA10 und EA11; EA14 zuletzt. Nichts davon blockiert die Mechanik der Ladestation.

**Tore:** (T1) Messung 2 negativ ⇒ E12, Konzept ohne Tobie-Wecken weiter. (T2) Messung 7 negativ (Pad 2 nicht belastbar) ⇒ eigene Zelle oder kein Wächter in Aus; ohne Wächter: Lauflicht erst nach dem Boot des ESP32 (≈ 2 s) statt sofort.
(T3) Messung 1 und 10 über 15 s ⇒ E13 mit Tobias.

### 10.3 Messliste am Muster

| # | Messung | Entscheidet |
|---|---|---|
| 1 | Bootzeit Pi 3A+: 5 V → Frühton, → `Bereit`, → Hörspiel; vor und nach jeder Maßnahme in 6.3 | E13, Ziele 6.1 |
| 2 | LPCD mit Tonie (ICODE SLIX2) und NTAG durch den Deckel: Schwelle, Feld-an-Zeit, Intervall 300 ms, Fehlweckungen (Hand, Metall); Reichweite mit TVDD 3,3 V gegen 5 V | E12, `LPCD_*` |
| 3 | Ruhestrom **Aus**: PiSugar (Hibernate), ESP32, PN5180, Regler, Pad-Schalter-Leck, MOSFET-Leck; µA über Stunden, auch kalt | Abschnitt 7 |
| 4 | Strom **Bereit**: mit/ohne WLAN, Ring stromlos, Leser Dauerabfrage / LPCD wach / ESP32 80 MHz / Light-Sleep mit USB | `wach`, Stufe 2, Abschnitt 7 |
| 5 | Pad 10: Pegel, Strom, Pull-Widerstand, `PAD_PULS_MS`, Anti-Mistouch aus (bleibt es nach Stromverlust?), Zeit Puls → 5 V | `PAD_PULS_MS`, H3 |
| 6 | „Einschalten bei Strom“: Flanke oder Pegel; nach Herunterfahren am Sockel; Ladegrenze des PiSugar | E3, E4, H6 |
| 7 | Pad 2 (BAT): Belastbarkeit, Schutzschaltung, Verhalten bei leerem Akku | H1, T2 |
| 8 | ESP32 aus BAT-Regler: Ruhestrom, USB-Enumeration ohne VBUS, keine Rückspeisung in den Pi-Port | H2 |
| 9 | Ring über ESP32: zweiter SPI-Host neben PN5180 (Flackern, Plan 8.4.4), Ring-Strom bei MOSFET aus (< 10 µA), Sichtbarkeit von 3 % und 5 % durch das Gehäuse | H4, 3.5 |
| 10 | Zeit Auflegen → Lauflicht (Aus), Knopf → Lauflicht, Auflegen → Hörspiel | Abschnitt 6.2 |
| 11 | Frühdienst: Python-Startzeit, ALSA gleichzeitig mit MPD (Ton über `softvol`) | 6.4 |
| 12 | Hauptknopf-Weg am Pi (`taste_befehl`/GPIO, B2) | E11 |
| 13 | Wiederholtes Wecken durch Powerbank oder Auto-Buchse, die Strom „neu“ geben | Sperre |
| 14 | `battery_power_plugged` an der einzigen Buchse (ohne Diode, R10); schwache 1-A-Quelle: sinkt der Akku trotz „Strom“? | R10, Tiefstand am Sockel |
| 15 | PN5180-Firmware-Version der Muster (≥ 4.0 für LPCD) | `caps` |
