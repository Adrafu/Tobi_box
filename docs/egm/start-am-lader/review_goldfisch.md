# Start am Lader: Goldfisch-Review des Design-Entwurfs

*   **Geprüft:** `docs/egm/start-am-lader/design_draft.md` (Stand 10.11.2026)
*   **Gegen:** `docs/egm/ladestation/software_folgen.md` (Abschnitt 10, S1 bis S11; zur Einordnung auch 2 bis 8),
    `docs/betrieb/pisugar-wecker.md`, `docs/protocol/*`, `docs/data-model.md`, `docs/designs/box-software.md`
    (CUJ 16, 20), Code `box/src/tobibox/` (`idle`, `lauf`, `bootid`, `led`, `app`, `power`, `core`, `sounds`,
    `quiet`, `session`, `sync`, `syncregel`, `nachfuehrung`, `config`) und Tests `box/tests/`.
*   **Rolle:** Goldfisch, ohne Gesprächsverlauf. Nichts geändert außer dieser Datei, nichts committet.

## Ergebnis in Kürze

16 Befunde: **2 hoch, 11 mittel, 3 niedrig.** Die Belege im Entwurf sind fast alle richtig (Liste in Abschnitt B).
Falsch ist ein Zeitverlauf (die Ladestand-Anzeige dauert nach dem Lauflicht nur etwa 3 s, nicht 5 s) und die Berufung
auf Entscheidung L für „nie zwei Töne“. Die Schwächen liegen im Ablauf: Wann genau gilt ein Start als „Start am Lader“,
was passiert nachts mit einem liegenden Tobie, und wo der Entwurf Entscheidungen stillschweigend auslegt.

---

## A. Befunde

### Hoch

**G1 (hoch): Zeile 9 der Tabelle ist zeitlich nicht begrenzt, und die Unterscheidung Start / Andocken hängt an einer einzigen Messung**
*   **Fundstelle:** Entwurf Abschnitt 2, Zeilen 9, 14 und Anmerkung unter der Tabelle (Zeile 159 bis 161); Abschnitt 3.3;
    `power.py:250-268, 275-290` (`pruefe` meldet nichts, wenn `pisugar-server` nicht antwortet).
*   **Problem:**
    1.  Zeile 9 gilt „beliebig außer `herunterfahren`“ und „beide Reihenfolgen“. Kommt die erste Messung erst spät (der
        `pisugar-server` war beim Start noch nicht da, `Power.start` fängt den Fehler ab, die nächste Messung kommt nach 2 bis 10 s,
        im schlimmsten Fall Minuten später), beginnt der Kurz-Modus mitten im Betrieb. Spielt dann schon ein Tobie, steht der
        Merker `kurz` auf wahr, aber Zeile 10 prüft nur **neue** `SitzungGeaendert`; die Sitzung hat sich nicht mehr geändert.
        Der Merker hängt dann fest, bis etwas anderes ihn löscht. `HaSyncAnstossen` und andere Zeilen verhalten sich
        im „Kurz-Modus“ anders (Zeile 3, 11), obwohl die Box längst normal läuft.
    2.  Meldet der PiSugar direkt nach dem Hochfahren kurz `false` und dann `true` (ob `battery_power_plugged` beim Start
        sofort stimmt, prüft Messung 2 nicht; sie prüft nur leeren und vollen Akku), wird aus dem Start ein „Andocken“
        (Zeile 14): Ton und Sync ja, aber **kein Kurz-Modus**. Die Box läuft dann 20 min am Sockel statt 2 min. Das ist
        genau der Fall, den S1 abdecken soll.
*   **Vorschlag:** Zeile 9 nur im Fenster nach `Bereit` (z. B. `STROM_START_WARTEN_S` + einige Sekunden, Konstante festlegen)
    und nur, wenn die Box nicht `belegt` ist und kein Tobie liegt. Außerhalb des Fensters: Zeile 14 oder nichts.
    Zusätzlich: Ein Wechsel `false` → `true` innerhalb dieses Fensters nach `einschalten` zählt noch als Start. Messung 2
    um „Wert von `battery_power_plugged` in den ersten 30 s nach dem Einschalten“ ergänzen. Test dafür in `test_idle.py`
    (Lader erst 30 s nach `Bereit`; Tobie spielt schon).

**G2 (hoch): Nachts mit liegendem Tobie widerspricht der Entwurf dem Zweck von S5**
*   **Fundstelle:** Entwurf 1.1 „Then 5“, 1.5 (Zeilen 1 und 2), Tabelle Zeile 10; `idle.py:236, 213-218`; `led.py:262-264`;
    `quiet.py:105-115, 141-160`.
*   **Problem:**
    1.  **„leiser“ schützt nicht vor dem Spielen.** S4 sagt „Nachts schützen die Leise-Zeiten“. Unter „leiser“ spielt der
        Tobie aber, nur leiser (`quiet.py`: nur „stumm“ blockiert den Start). Jeder Stromstoß nachts (Stromausfall, Powerbank
        im Zimmer, Sockel wackelt) startet die Box und das Hörspiel in einem Kinderzimmer. S1 („gutmütig“) und S4
        zusammen machen das zur Regel. Der Entwurf nennt es nicht.
    2.  **Zeile 10 beendet den Kurz-Modus bei jedem liegenden Tobie, auch wenn nichts spielt.** Unter „stumm“ bleibt die
        Sitzung `gehalten`: kein Hörspiel, aber der Kurz-Modus ist weg und die 20-min-Regel gilt (Entscheidung O). Die
        Box zeigt dann 20 min lang den bernsteinfarbenen Pause-Ring (`led.py:262-264`: Leerlauf mit liegendem Tobie zeigt
        `PAUSE`), gedimmt auf 4 % (10 % × 0,4), und der Entwurf lässt dazu den leisen `hinweis`-Ton für „erkannt“ gelten
        (1.5, Zeile 1). Das ist das Gegenteil von „Ring gedimmt, kein Ton, Lauflicht aus“ (S5). S3 meint „Tobie
        **auflegen**“, nicht „es liegt einer“.
*   **Vorschlag:**
    *   Zeile 10 nur bei `spielt` oder `unbekannt` (also `belegt`), oder bei einem **Auflegen** nach `Bereit`; ein beim
        Start liegender Tobie in `gehalten` / `pausiert` beendet den Kurz-Modus nicht.
    *   Frage an Tobias (Q2): Soll „leiser“ den Selbststart eines Hörspiels beim Start am Lader verhindern wie „stumm“?
        Wenn nein, im Design festhalten.

### Mittel

**G3 (mittel): Stille Auslegungen von S1, S2, S3, S8 ohne Kennzeichnung als offene Frage**
*   **Fundstelle:** Entwurf 0 (Punkt 1), 1.1, 1.2, 2 (Zeilen 11, 15), 3.1, 3.4; `software_folgen.md` Abschnitt 10 und 3.2.
*   **Problem:** Das Meiste ist in Abschnitt 5 als Frage geführt. Nicht gekennzeichnet sind:
    1.  **S1 „Jeder Start mit Strom … Kein Merker“.** Der Entwurf nimmt „Dienst-Neustart“ aus (G, 06.11.) und schreibt dafür
        einen Marker bei **jedem** Start (`lauf.json`, D1). Die Schleifenbremse (3.4) nimmt weitere Starts aus. Das ist eine
        Auslegung von S1; Entscheidung G betraf nur den Tobie. Tobias sollte bestätigen: „Nach Update oder Absturz keine
        Rückmeldung und kein Kurz-Modus.“
    2.  **S3 „HA-Befehl“.** Der Entwurf zählt nur angenommenes `HaSyncAnstossen`, `HaUpdateAnstossen` und Lernmodus-Start
        (Zeile 11). Abgelaufene oder abgelehnte Befehle zählen nicht, `HaLernmodusAbbruch` nie. Plausibel, aber nicht S3.
    3.  **S8 „10 s entprellt“.** Die Sperre rechnet im Entwurf vom **letzten Wechsel** (auch vom Abziehen); `software_folgen.md`
        3.2 sagt: nach einer **Rückmeldung** 10 s Pause. Verhalten unterscheidet sich (Plug 0 s, Abziehen 12 s,
        Plug 14 s: Entwurf still, `software_folgen` Rückmeldung). Siehe auch G5.
    4.  **S2 „Sync hält wach“.** `LADER_NACHLAUF_S` (30 s) ist neu und gehört zu S6, nicht zu S2 (siehe G9, G15).
    5.  **S2 „ab Ende der Rückmeldung“.** Umgesetzt als „ab `Bereit`/erster Messung + 7 s“, die 7 s stimmen nicht (G4).
*   **Vorschlag:** Diese fünf Punkte in Abschnitt 5 als Fragen F13 bis F17 aufnehmen oder als Auslegung kennzeichnen.

**G4 (mittel): Die Ladestand-Anzeige dauert nach dem Lauflicht etwa 3 s, nicht 5 s; die 7 s sind doppelt festgelegt**
*   **Fundstelle:** Entwurf 1.1 „Then 1“ (Zeile 46), C9 (`LADER_RUECKMELDUNG_S` = 7); `led.py:207-210, 233-241, 244-258`.
*   **Problem:** `LaderGeaendert` setzt `_akku_bis = jetzt + 5 s` (`akku_zeigen`). `Bereit` startet das Lauflicht
    (2 s, Rang vor Akku). In `zustand()` gewinnt Aufwachen, danach Akku bis `_akku_bis`. Es bleiben also etwa 3 s Ladestand
    (5 s minus 2 s minus Abstand zwischen den Ereignissen). Das gilt schon im Bestand (Lader kommt Millisekunden nach
    `Bereit`) und mit der neuen Reihenfolge (Lader vor `Bereit`) erst recht. Außerdem steht die Zahl 7 in `idle.py`,
    die Quellen (`AUFWACHEN_S`, `AKKU_ANZEIGE_S`) in `led.py`: zwei Wahrheiten.
*   **Vorschlag:** Entweder in `led.py` `akku_zeigen` beim Start erst nach dem Lauflicht beginnen lassen (`_akku_bis` =
    Ende Aufwachen + 5 s), oder die Beschreibung auf „etwa 3 s“ ändern. `LADER_RUECKMELDUNG_S` aus `led`-Konstanten
    ableiten oder nur als Kommentar führen. Test in `test_led.py` mit Zeitverlauf.

**G5 (mittel): „Wackelt der Kontakt, bleibt es still“ stimmt für den Ring nicht**
*   **Fundstelle:** Entwurf 1.2 (Zeile 77 bis 79), Konflikt-Tabelle Zeile 178, Tabelle Zeilen 14, 15; `led.py:237-241`.
*   **Problem:** Die Sperre sitzt in `idle` und wirkt nur auf `TonSpielen` und `SyncStarten`. Der Ring liest `LaderGeaendert`
    direkt und setzt bei **jedem** Wechsel die 5 s Akku-Anzeige neu (blau / Ampel im Wechsel). Ein wackelnder Sockel lässt
    den Ring also flackern. Die Aussage „danach still“ ist falsch, und „Kein neuer Befehl `LaderMelden`“ (Kurzfassung 3)
    ist gerade deshalb ein Nachteil: `software_folgen.md` hatte `LaderMelden` genau dafür vorgesehen. Zusätzlich fehlt, dass
    die 2-s-Abfrage kürzere Aussetzer gar nicht sieht (Messung 5 deckt das teilweise ab).
*   **Vorschlag:** Entscheiden (Q10), ob der Ring entprellt wird. Wenn ja: Mindestabstand für `akku_zeigen` im `led`
    (kein neuer Vertrag nötig) oder `idle` gibt einen Befehl aus. Konflikt-Tabelle Zeile 178 anpassen.

**G6 (mittel): Helligkeit: Doppel-Dimmung unter „stumm“, Nebenwirkung der Rundung, Lauflicht-Regel widerspricht Abschnitt 3.2**
*   **Fundstelle:** Entwurf 1.3, L6, 3.2; `led.py:64, 112-119, 161-168, 280-283`.
*   **Problem:**
    1.  `LedLogik.ring` multipliziert **alle** Bilder unter „stumm“ mit 0,4 (`led.py:280-283`). Setzt `_akku()` 3 % absolut,
        werden daraus 1,2 % und `int(1,2 × 31 / 100)` = 0, also dunkel. Der Entwurf schreibt „3 % statt 15 % × 0,4“, sagt aber
        nirgends, dass die Akku-Anzeige den Faktor umgehen muss.
    2.  „Stufe mindestens 1“ in `apa102_rahmen` ändert das Verhalten global: Gute Nacht unter „stumm“ (heute immer dunkel,
        wie der Entwurf selbst bemerkt) würde plötzlich sichtbar, mit 3,2 %. Das ist eine Verhaltensänderung außerhalb
        dieses Themas.
    3.  Abschnitt 3.2 sagt für `einschalten = false`: „Lauflicht wie heute“ (25 % auch nachts). L6 macht das Lauflicht
        aber generell von `ruhe` und Uhr abhängig (`Bereit` ruft `aufwachen` bedingungslos, `led.py:233-234`). Der
        Update-Neustart ist der Normalfall bei S6 (Andocken abends), das Lauflicht nachts gerade dort sichtbar.
    4.  `leiser` „5 %“: `int(5 × 31 / 100)` = 1 = 3,2 %. Messung 9 prüft das; gut.
*   **Vorschlag:** Akku-Anzeige in `ring()` vom Faktor ausnehmen und Werte (15 / 5 / 3 %) direkt setzen. „Mindest-Stufe 1“
    nur für den Akku-Zustand, nicht global. Lauflicht bei `Bereit` einheitlich nach `ruhe` (auch bei `einschalten = false`),
    3.2 anpassen.

**G7 (mittel): `lauf.json` als Start-Marker hat Lücken**
*   **Fundstelle:** Entwurf 3.1, D1; `app.py:587-589, 424, 522-525, 1076-1078`; `lauf.py:41-55, 73-82`.
*   **Problem:**
    1.  `Herunterfahren` löscht `lauf.json` **vor** dem Poweroff (`app.py:588`). Schlägt es fehl
        (`HerunterfahrenFehlgeschlagen`, `_herunterfahren` wird zurückgesetzt, `app.py:424`), schreibt niemand die Datei neu.
        Ein späterer Dienst-Neustart (Update!) gilt dann als Einschalten: Ton `lader`, Start-Sync, Kurz-Modus. Heute
        betrifft das nur die Tobie-Wiederaufnahme, mit dem Entwurf auch die Box-Rückmeldung. Tabelle Zeile 7 und 8
        erwähnt den Marker nicht.
    2.  `lauf.nachfuehren` schreibt nur bei Wechsel des Tobies (`uid != bisher`). Der Entwurf verlangt einen zusätzlichen
        Schreibvorgang nach `Bereit`. Das ist in L1 genannt, aber nicht, wie sich beide Schreiber vertragen
        (Reihenfolge, `neustart_uid` bleibt).
    3.  Am Mac gilt die Systemstartzeit als Kennung (`bootid.py:30-35`). Jeder Dienst-Neustart am Mac ist ein
        Dienst-Neustart, einen echten „Start am Lader“ gibt es nur mit `--einschalten`. Das ist in L1 vorgesehen; im Entwurf
        steht nicht, dass die Mac-Simulation ohne die Option den Hauptpfad **nie** prüft (CUJ 21 braucht sie in jedem Test).
*   **Vorschlag:** Nach `HerunterfahrenFehlgeschlagen` den Marker neu schreiben (Zeilen 7 / 8 der Tabelle, `app`). Test in
    `test_bootid_lauf.py`.

**G8 (mittel): „Erste Messung vor `Bereit`“ ist ein Eingriff in jeden Start**
*   **Fundstelle:** Entwurf 3.3, C1, L1; `app.py:921-937, 944-955`; `power.py:250-268`.
*   **Problem:**
    1.  `Power.start` macht mindestens vier Anfragen an den `pisugar-server` (`rtc_time`, `rtc_rtc2pi`,
        `battery_power_plugged`, `battery`). Mit 2 s Frist verzögert das **jeden** Start bis zu 2 s, auch wenn der Server
        fehlt oder langsam ist. Bei Abbruch durch `wait_for` bleibt unklar, ob `_strom_lauf` `start()` erneut aufruft
        (`app.py:947-955`) und `rtc_rtc2pi` zweimal läuft.
    2.  Die Reihenfolge der Ereignisse im Kern hängt davon ab, dass die Ereignisse **vor** `Bereit` eingereiht und verarbeitet
        sind (FIFO). Der Entwurf sagt es nicht ausdrücklich; sonst kann `Bereit` vor `ZeitquelleGeaendert` stehen.
    3.  Die Reihenfolge der systemd-Einheiten (`After=pisugar-server`) ist nirgends genannt. Ohne sie wird die 2-s-Frist
        beim echten Einschalten oft gerissen (der Server startet auf dem Pi 3A+ langsam), und G1 greift.
*   **Vorschlag:** In C1 und L1 festhalten: Messung läuft **einmal** (Ergebnis an `_strom_lauf` weiterreichen), `Bereit` erst
    nach `_leere_ereignisse`, Einheit mit `After=` und Messung der echten Dauer (Messung 3 erweitern um „Dauer von
    `Power.start`“). Alternative prüfen: Statt `Bereit` zu verzögern, `start` nur durch `idle` ausgeben lassen (siehe G15).

**G9 (mittel): S6 Variante A (Merker in HA) hat offene Stellen**
*   **Fundstelle:** Entwurf 1.4, 4.3 (H1), 4.5; `idle.py:304-317`; `app.py:609-620`.
*   **Problem:**
    1.  **Abweichung von S6.** S6 sagt „die Box holt es“. Variante A lässt HA senden. S6 erwartete „Vertragsänderung in
        `mqtt-v1.md` und `core-interface.md`“. Mit A ändert sich am Box-Vertrag fast nichts (M2 ist nur ein Satz). Das kann
        richtig sein, ist aber eine Abweichung von der Entscheidung und gehört in die Fragen (steht als F8, aber als
        Empfehlung, nicht als Abweichung von S6).
    2.  **`idle` nimmt an, `app` lehnt ab.** `idle` nimmt `HaUpdateAnstossen` an und beendet den Kurz-Modus (Zeile 11),
        danach lehnt `app` ab (`UPDATE_NOCH_NICHT_TEXT`, heute immer; mit 3b aus Gründen des Updaters). Ergebnis: Box 20 min
        wach ohne Update. HA sieht `befehl_abgelehnt`; H1 (d) definiert „angenommen“ nicht über das Ereignis, und H1 (c)
        versucht es bis 10 min erneut, obwohl die Box nach 2 min aus ist.
    3.  **Fenster.** HA braucht `netz = home`, `zustand ≠ spielt` und `sync ≠ laeuft`. Der Start-Sync blockiert beides, bis er
        fertig ist; `LADER_NACHLAUF_S` (30 s) ist die ganze Reserve. H1 (b) nennt „bis 10 min nach der Flanke“ als Frist, die
        Box ist aber nach 127 s + 30 s weg. HA weiß nicht, ob die Box noch läuft (`kurz` ist nicht im Status).
    4.  **Andockflanke in HA.** „Box wird `online` und meldet `lader = true`“ trifft auch bei HA-Neustart, MQTT-Wiederverbindung
        und Dienst-Neustart der Box zu (retained Status). Ein Update zu einem unerwünschten Zeitpunkt wäre die Folge
        (Bedingung `zustand ≠ spielt` schützt nur teilweise).
    5.  Der Merker liegt in einem HA-Speicher, der in `data-model.md` nicht beschrieben ist (G12).
*   **Vorschlag:** In H1 „angenommen“ = `HaUpdateAnstossen` angenommen **und** `UpdateStarten` nicht abgelehnt. Frist (b) auf
    die tatsächliche Laufzeit der Box abstimmen (≤ 3 min), Andockflanke nur bei `lader` von `false` / unbekannt auf `true`
    **bei laufender Verbindung** oder nach `lauf`-Start-Kennzeichen. `LADER_NACHLAUF_S` erst mit L9 einführen.

**G10 (mittel): Die Schleifenbremse löst das Problem nicht und kostet drei Vertragsstellen**
*   **Fundstelle:** Entwurf 3.4, C11, M3, D2, L1; Messung 1 (6.2).
*   **Problem:** Zwei Fälle: (a) Der PiSugar startet nicht neu → Bremse unnötig. (b) Er startet bei Strom neu →
    Bremse macht aus 2,5-min-Schleife eine ~20-min-Schleife (immer wieder `einschalten = false`, Lauflicht, `start`-Ton), das
    Gerät lässt sich am Sockel nie ausschalten, und die richtige Antwort ist laut Entwurf selbst „R8 zurücknehmen“. Es
    bleibt kein Fall, in dem die Bremse die richtige Lösung ist. Kosten: `ende.json` (neue Datei, D2), Konstante, Fehlercode
    (C11, M3), zusätzliche Ausnahme von S1 (G3), eigene Tests, Abhängigkeit von `zeit_ok`.
*   **Vorschlag:** Streichen. Messung 1 vor L1 (so steht es schon). Wird eine Schleife gemessen, R8 zurücknehmen; wird keine
    gemessen, ist die Bremse überflüssig. Wenn Tobias eine Absicherung will, reicht ein Eintrag im Protokoll
    (kein Vertrag).

**G11 (mittel): Abziehen im Kurz-Modus: Box geht beim Hochheben aus**
*   **Fundstelle:** Entwurf 1.2 „Abziehen“, Zeile 13, F4/K4; `software_folgen.md` 2.2, 3.4 und 8 (Frage 3).
*   **Problem:** `software_folgen.md` hatte „Abziehen“ in der Liste der Dinge, die den Kurz-Modus beenden (Empfehlung);
    Tobias' S3 nennt es nicht. Der Entwurf legt das als „läuft weiter“ aus. Folge: Ein Kind, das die Box in den ersten
    2 min vom Sockel nimmt (der typische Griff nach dem Aufsetzen), hat eine Box, die in der Hand ohne Vorwarnung ausgeht
    (Akku-Ring 5 s ist alles). Ob das gewollt ist, ist keine Folgerung aus S3, sondern eine neue Entscheidung.
*   **Vorschlag:** Q4 an Tobias. Technisch einfach: Zeile 13 beendet den Kurz-Modus (20 min ab jetzt).

**G12 (mittel): Vertragsänderungen: Lücken und eine rückwärtsinkompatible Vorgabe**
*   **Fundstelle:** Abschnitt 4; `config.py:235-238, 475`; `core-interface.md:194`; `mqtt-v1.md:601`.
*   **Problem:**
    1.  **`Bereit.einschalten: bool = True`** (C1) ändert das Verhalten **jedes** bestehenden Aufrufers von `Bereit()` (Tests,
        Simulation): Mit Lader beginnt der Kurz-Modus. Rückwärtskompatibel wäre `False` (altes Verhalten) oder ein Pflichtfeld.
    2.  **Fehlende Stellen:** (a) HA-seitiger Speicher des Merkers (nur im Text von H1, nicht in `data-model.md`); (b) neue
        Konfigurationsschlüssel `[strom] lader_intervall_s` und `sim_lader` (`_STROM_SCHLUESSEL` in `config.py:235-238` muss
        sie kennen, sonst werden sie ignoriert; Dokumentation der `tobibox.toml` fehlt in L0); (c) die HA-Entität „Lader“ hat
        `device_class` für Ladezustand (`mqtt-v1.md:601`); „Strom am Eingang aus irgendeiner Quelle“ ist anderes, M1 ändert nur
        den Text; (d) `ZustandMelden` / Status zeigt `kurz` nicht, H1 (b) bräuchte es (G9); (e) `core-interface.md:322`
        (`SyncStarten`) und die Statusfelder `sync.grund` bleiben richtig, sollten aber als geprüft vermerkt sein.
    3.  **Wiederholung:** C3, C7, C9 streichen die Wiederholung, obwohl F1 offen ist (siehe G3). Freigabe der Verträge sollte
        erst nach Q1 erfolgen.
*   **Vorschlag:** `Bereit.einschalten` ohne Vorgabe oder mit `False`; die genannten Stellen in L0 ergänzen; Verträge erst
    nach Klärung von Q1 bis Q6 freigeben.

**G13 (mittel): Umsetzungsplan: L1 ist nicht schneidbar, Abhängigkeiten und Tests lückenhaft**
*   **Fundstelle:** Abschnitt 6.1.
*   **Problem:**
    1.  **L1** enthält sechs Themen (Ereignis, `lauf`, Startreihenfolge, `ende.json` / Bremse, Sim-Optionen, Tests). Nicht
        einzeln testbar. Vorschlag: L1a `einschalten` (Ereignis + `lauf` + Test), L1b Startreihenfolge, L1c Sim-Optionen, die
        Bremse entfällt (G10).
    2.  **L2** (idle) braucht `TonSpielen("lader")`; `Literal` wird nicht erzwungen, aber `sounds` / `core` (L4) müssen den Ton
        kennen, damit `test_app_toene`-Pfade laufen. L2 hängt also auch an L4, und L7 an L2, L4, L6 (so steht es), aber L2 / L4 / L6
        ändern alle `events.py` bzw. `config.py` (Merge-Konflikte).
    3.  **L0** (Haiku) soll 20 Vertragsstellen mit genauem Wortlaut einarbeiten. Verträge ändern Agents nicht eigenmächtig
        (`CLAUDE.md`); der Wortlaut ist vorgegeben, aber 20 Stellen quer über vier Dokumente sind kein Haiku-Boilerplate
        (Sonnet oder Koordinator, danach Gegenlesen).
    4.  **Fehlende Tests:** Zeitverlauf Ring (G4); Entprellung (G5); Marker nach fehlgeschlagenem Herunterfahren (G7);
        Start nach langer Verzögerung der ersten Messung (G1); Doppelstart von `Power.start` (G8); Andocken im Hotspot; Andocken
        während `herunterfahren`; Kurz-Modus mit Abziehen und Wiederanstecken. Die Tabelle in Abschnitt 2 ist als
        Abnahme gut; die Zeilen 3, 7, 8 und 13 brauchen je einen Testfall.
    5.  **Mac:** `sim power` misst sofort (`app.py:360-369`), die 2-s-Abfrage (L3) und `LADER_SPERRE_S` sind am Mac nur mit
        simulierter Uhr prüfbar. L7 nennt „Simulation, Uhr“; sagen, dass die CUJ-Tests `box.sende` / `warte` nutzen.
*   **Vorschlag:** Plan wie oben schneiden; Testliste in 6.1 ergänzen.

### Niedrig

**G14 (niedrig): Entscheidung L falsch zitiert**
*   **Fundstelle:** Entwurf 1.1 „Then 1“ (Zeile 46), 3.3, K7; `core-interface.md:34, 637, 658, 813`.
*   **Problem:** Entscheidung L heißt: „Es spielen nie zwei Sachen **gleichzeitig**“ (Töne nacheinander auf einer Spur,
    Ton vor Hörspiel). „Ein Ton, nie zwei“ ist eine neue Regel (1a), keine Folge von L. Zwei Töne **nacheinander** wären
    mit L vereinbar. Die Regel 1a ist trotzdem sinnvoll; sie braucht eine eigene Begründung.
*   **Vorschlag:** In C6 die Begründung ändern („zwei Töne hintereinander verwirren das Kind“), L nur für „Ton vor Hörspiel“
    nennen.

**G15 (niedrig): Was sich streichen oder verschieben lässt**
*   **Fundstelle:** Abschnitte 1.2, 2, 3.4, 4.1, 4.5, 6.1.
*   **Vorschläge, nach Gewinn geordnet:**
    1.  **Schleifenbremse** streichen (G10): `ende.json`, `SCHLEIFE_S`, C11, M3, D2.
    2.  **`LADER_NACHLAUF_S`** erst mit L9 (3b) einführen; ohne Merker ist die Konstante tot (4.5, Tabelle „Jetzt“).
    3.  **Eigene Lader-Abfrage alle 2 s** (`lader_intervall_s`): Ein gemeinsames `intervall_s` von 3 s für Lader und Akku
        spart Konfiguration, Test und Code in `Power.lauf`; Messung 5 entscheidet. Erst messen, dann trennen.
    4.  **Neuer Ton `lader.wav`** (C4, C5, C6, C10, D3, L4, L5, Pegelzweig in `sounds`, Lautheit): Fragen, ob `start`
        oder `hinweis` reichen (Q7). Mit `start` entfielen Regel 1a, die Umstellung der Reihenfolge (für den Ton) und der
        Pegelzweig.
    5.  **Zeilen 10, 11, 12** der Tabelle (alle: „Kurz aus, Zähler 20 min ab jetzt“) als **eine** Zeile mit Aufzählung der
        Auslöser schreiben.
    6.  **„Uhr unsicher“** als eigenes Kriterium in C5 / LED: `quiet.py:105-115` bildet unsichere Uhr bereits auf `leiser`
        ab, wenn ein Fenster mit „leiser“ konfiguriert ist (sonst `normal`). Prüfen, ob die zweite Regel nötig ist oder
        `ruhe` genügt.

**G16 (niedrig): Doku-Nachziehliste unvollständig**
*   **Fundstelle:** L8; `docs/betrieb/mac-prototyp.md:1730`; `docs/plan/stueckliste-und-psp.md:25, 742`;
    `docs/betrieb/pisugar-wecker.md:182-188`.
*   **Problem:** Nicht genannt, aber betroffen: Plan 3.16 (Zeile 25) und die Entscheidungszeile „Start am Lader“ (Zeile 742)
    mit der 6-mal-Wiederholung, `mac-prototyp.md` Zeile 1730 (Probe „Start-Sync am Lader und dessen Wiederholung“),
    `pisugar-wecker.md` Abschnitt 6 („Erledigt Rev. 3.16“ wird wieder offen). Code-Kommentare in `idle.py` (Kopf) und
    `events.py`. Der Entwurf nennt sie nicht einzeln.
*   **Vorschlag:** L8 um diese Stellen ergänzen.

---

## B. Geprüfte Belege

Stichprobe, 36 Fundstellen. Ergebnis: **richtig**, wenn nicht anders vermerkt.

| Beleg im Entwurf | Ergebnis |
|---|---|
| `idle.py:168-178` Start-Prüfung ohne Unterscheidung Einschalten / Dienst-Neustart | richtig |
| `idle.py:114-116` `blockiert` (Lernmodus, Sync, Update, offen, Wiederholung) | richtig |
| `idle.py:186-190, 244-250` Bedienung setzt Zähler zurück | richtig |
| `idle.py:12-14` HA-Befehle setzen den Zähler nicht zurück | richtig |
| `idle.py:213-215` Zähler beginnt mit dem ersten Ereignis | richtig |
| `idle.py:252-254` Tiefstand am Lader ignoriert | richtig |
| `idle.py:329-355` im Herunterfahren nur nachführen | richtig |
| `events.py:291-293` `Bereit` ohne Felder | richtig |
| `lauf.py:23-38, 73-82` Marker nur beim Tobie-Wechsel und Dienst-Ende | richtig |
| `bootid.py:28-39, 6` Kennung, `None` = Einschalten | richtig |
| `app.py:587-589` Marker löschen beim Herunterfahren | richtig |
| `app.py:924 / 937 / 953` `Bereit` vor `power`-Start | richtig (Bereit 924, Stufe 3a 937, `_strom_lauf` 953) |
| `app.py:612-620` Update bis 3b abgelehnt | richtig |
| `app.py:634-657` Wartezeit auf Netz-Klasse | richtig |
| `app.py:360-369` `sim power` misst sofort | richtig |
| `app.py:531-536` Takt startet Sync | richtig |
| `power.py:156-162` Lader = `battery_power_plugged` | richtig |
| `power.py:209`, `config.py:222` Abfrage alle 10 s | richtig |
| `power.py:291-309` Tiefstand nur sicher ohne Lader | richtig |
| `led.py:112-119` Rundung `int(h × 31 / 100)` (5 % → 1, 3 % → 0) | richtig |
| `led.py:161-168` Akku-Anzeige 15 % | richtig |
| `led.py:171-179, 233-234` Lauflicht bei jedem `Bereit` | richtig |
| `led.py:237-241` Ladestand 5 s bei `LaderGeaendert` | Zeile richtig; **die Folgerung „Lauflicht, dann 5 s Ladestand“ ist falsch** (G4) |
| `led.py:280-283` `stumm` ×0,4 | richtig (und Ursache von G6.1) |
| `core.py:44, 116-121` Regel 2 und `_TOENE_UNTER_STUMM` | richtig |
| `sounds.py:60-70` `pegel` | richtig |
| `session.py:844-845` `_bereit` spielt `start` | richtig |
| `net.py:202-216`, `app.py:225-229` Zeit am Pi anfangs unbekannt | richtig |
| `sync.py:176-177, 226` Takt startet nach Netzwechsel / ohne `letzter_start` | richtig |
| `syncregel.py:29-32` Hotspot mit Lader oder Akku über 50 % | richtig |
| `test_idle.py:325-330` (liegt in `box/tests/unit/`) „spätes Einstecken zählt nicht“ | richtig (Test steht bei ca. 324 bis 328; Pfad ergänzen) |
| `test_core_stufe3a.py:61`, `test_befunde_stufe3a_4.py:407-422` | richtig; der zweite Test prüft `wdh_bei`, das Feld entfällt |
| `core-interface.md` 194, 227, 316, 319, 359, 468-470, 1344-1353 | richtig |
| `mqtt-v1.md` 71, 76, 156, 220, 601; `data-model.md` 134, 150, 208 | richtig |
| `pisugar-wecker.md:81-114, 116-164, 180-191` | richtig |
| „Entscheidung L = nie zwei Töne“ | falsch, siehe G14 |

---

## C. Fragen, die nur Tobias entscheiden kann

1.  **Q1 Wiederholung des Start-Syncs:** Streichen (Entwurf) oder erhalten, z. B. nur außerhalb des Kurz-Modus? Folge: Die
    Lücke „Wecker nachts, WLAN noch nicht da“ aus `pisugar-wecker.md` Abschnitt 6 ist wieder offen.
2.  **Q2 „leiser“ und Selbststart:** Soll ein Hörspiel beim Start am Lader unter „leiser“ von selbst losgehen (S4 wörtlich)
    oder nur außerhalb jeden Leise-Fensters? Ein Stromstoß nachts startet sonst die Box.
3.  **Q3 Liegender Tobie ohne Wiedergabe** (unter „stumm“, `gehalten`): Beendet er den Kurz-Modus (Entwurf, 20 min Pause-Ring)
    oder nicht (2 min)?
4.  **Q4 Abziehen im Kurz-Modus:** Beendet es den Modus (Box bleibt 20 min an) oder läuft die Frist weiter (Box geht beim
    Hochheben nach spätestens 2 min aus)?
5.  **Q5 Dienst-Neustart:** Bestätigen, dass nach Update oder Absturz keine Rückmeldung und kein Kurz-Modus kommt, auch wenn
    S1 „jeder Start mit Strom“ sagt. Und: Lauflicht nachts nach einem Update-Neustart aus?
6.  **Q6 S6 Variante A:** HA sendet den Befehl (Entwurf) statt „die Box holt es“ (S6 wörtlich)? Merker-Verfall 30 Tage in
    Ordnung? Frist, in der HA nach dem Andocken reagieren muss (ca. 2 bis 3 min), in Ordnung?
7.  **Q7 Ton:** Neuer Ton `lader.wav` oder `start` / `hinweis` wiederverwenden (spart sechs Vertragsstellen und eine Regel)?
8.  **Q8 Schleifenbremse:** Streichen und nur messen (Empfehlung des Goldfischs), oder behalten?
9.  **Q9 HA-Befehle, die den Kurz-Modus beenden:** Nur Sync, Update, Lernmodus-Start (Entwurf) oder jeder angenommene
    HA-Befehl (S3 wörtlich)? Und: Kopfhörer einstecken ignorieren (F10)?
10. **Q10 Entprellen:** Sperre vom letzten Wechsel (Entwurf) oder nach der letzten Rückmeldung (`software_folgen.md` 3.2)?
    Soll auch der **Ring** entprellt werden (heute flackert er bei Wackelkontakt)?
11. **Q11 Gute Nacht unter „stumm“:** Heute unsichtbar (Rundung). Darf „Stufe mindestens 1“ das ändern (sichtbar mit ~3 %)?
12. **Q12 Entität „Lader“ in HA:** Name und Geräteklasse so lassen, obwohl sie jetzt „Strom am Eingang“ heißt?
