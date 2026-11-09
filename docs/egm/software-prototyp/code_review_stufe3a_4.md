# Code-Review Goldfisch: Verdrahtung Stufe 3a (AP 3.7) und Stufe 4 (AP 4.8)

Stand: Commit `50096ed` (`git diff 1dae8ac..HEAD -- box/src`). Prüfer ohne Vorwissen. Maßstab: `docs/protocol/core-interface.md`,
`mqtt-v1.md`, `data-model.md`, `docs/designs/box-software.md`. Die parallel nachgetragenen Vertragsänderungen aus AP 4.8
(Zähler durch Bedienung zurückgesetzt, Start-Sync-Wiederholung, `nicht_eingerichtet`, vorläufige Ring-Farben) gelten als gewollt
und sind nicht beanstandet.

Lauf: `pytest -q tests/unit tests/cuj` gibt 2763 bestanden. Eigene Wegwerf-Proben liegen unter
`/tmp/claude-0/-home-user-Tobi-box/87837eca-ee4b-54f9-bcf7-9cb39d3c88c0/scratchpad/rvS4/` (`probe1.py`, `probe2.py`, `probe3.py`,
`test_probe_race.py`). Im Repo wurde nichts geändert.

Schwere: **Hoch** = kann auf dem Pi Schaden oder Stillstand verursachen. **Mittel** = falsches Verhalten in realen Lagen.
**Niedrig** = Randfall, Robustheit oder Test-Lücke.

---

## Befunde

### B1 (Hoch) Fehlgeschlagenes Herunterfahren ist endgültig: die Box schaltet nie wieder ab

* **Wo:** `idle.py:184-185` und `idle.py:312-313` (Zustand `herunterfahren` ist ein Endzustand, `step` kehrt sofort zurück),
  `power.py:157-160` (`PiSugarStrom.herunterfahren` prüft den Rückgabecode nicht, kein Zeitlimit), `app.py:500-505`
  (`_herunterfahren = True`, `lauf.loesche` vor dem Poweroff), `led.py:248` (Ring zeigt `aus`).
* **Szenario:** `systemctl poweroff` schlägt fehl (Dienst ohne Rechte, polkit lehnt ab, `abschalt_kommando` falsch) oder der Befehl
  fehlt. `create_subprocess_exec` wirft `FileNotFoundError`, der Ausführer loggt nur `befehl_fehler`. Bei Rückgabecode ungleich 0 kommt
  nicht einmal das. `idle` bleibt für immer in `herunterfahren`. Ring dunkel, HA zeigt `herunterfahren`, die Box spielt aber weiter.
  Ohne `[strom]` (`power is None`) und am Mac gilt dasselbe.
* **Beleg (`probe3.py`):** Erstes `Hauptknopf("lang")` gibt `Herunterfahren`. Das zweite gibt nichts. Nach 21 min Leerlauf kommt kein
  weiteres. Ein späteres `AkkuTiefstand` gibt ebenfalls kein `Herunterfahren` mehr. Ein Tiefstand würde also nie mehr abschalten, der
  Akku läuft leer und die Box fällt hart aus.
* **Vorschlag:** `PiSugarStrom.herunterfahren` prüft den Rückgabecode und das Zeitlimit und meldet einen Fehler. Dazu ein Ereignis
  (z. B. `HerunterfahrenFehlgeschlagen`), das `idle` zurück nach `aktiv` oder `leerlauf` setzt, mit neuem Zähler. `_herunterfahren` und
  `lauf.loesche` erst nach Erfolg setzen. Ohne Erfolg zusätzlich ein `fehler`-Ereignis an HA.

### B2 (Mittel) Auf dem Pi hat der Hauptknopf keine Quelle, wenn `pin_haupt` fehlt

* **Wo:** `power.py:280-286` (`Power.taste`), `config.py` (`pin_haupt` optional), `core-interface.md:203` (Hauptknopf „kommt von
  `power` oder von `controls`“).
* **Szenario:** Der Vertrag und `controls.py` setzen voraus, dass am Pi der PiSugar-Taster `Hauptknopf` über `power` liefert.
  `Power.taste` hat aber keinen Aufrufer: weder `app.py` noch `power.lauf` noch ein Abonnement am `pisugar-server`. Nur
  `tests/unit/test_power.py:125` ruft sie. Ohne `[tasten] pin_haupt` gibt es am Pi weder Pause und Weiter noch Abschalten per
  Hauptknopf lang.
* **Beleg:** `grep -rn "taste(" box/src` findet nur die Definition.
* **Vorschlag:** Entweder die PiSugar-Taste verdrahten (Ereignisse des `pisugar-server` lesen und `power.taste` aufrufen), oder in
  Design und `config.example.toml` festhalten, dass `pin_haupt` auf dem Pi Pflicht ist, und `quelle="gpio"` ohne `pin_haupt` mit einer
  Warnung beantworten. Der Plan (`stueckliste-und-psp.md:501`, 3.2.4) führt das Thema als offen. Es sollte als offener Punkt in
  `docs/plan/` stehen.

### B3 (Mittel) Kopfhörer-Schaltkontakt nicht lesbar: der Gehörschutz fällt stillschweigend weg

* **Wo:** `headphones.py:149-160` (`start`), `headphones.py:162-172` (`pruefe`), `app.py:796-798`.
* **Szenario:** `gpioget` fehlt, der Pin ist falsch oder die Rechte fehlen. `Buchse` loggt eine Warnung (einmal) und sendet kein
  `Kopfhoerer`. Der Kern bleibt auf „kein Stecker“, also gilt die Lautsprecher-Grenze (`lautstaerke.max`, Vorgabe 50) und nicht die
  Kopfhörer-Grenze (30), und der Ausgang bleibt `lautsprecher`. Ein Kind mit Kopfhörern hört dann mit der höheren Grenze, wenn die
  Hardware den Ton trotzdem an die Buchse führt. HA und der Status erfahren nichts davon (kein `fehler`-Ereignis, kein Statusfeld).
* **Vorschlag:** Lesefehler an HA melden (`fehler`-Ereignis, Prüfpunkt oder Statusfeld). Prüfen und festlegen, welcher Zustand bei
  „unbekannt“ der vorsichtigere ist (z. B. Kopfhörer-Grenze anwenden, solange die Buchse nicht lesbar ist). Das ist eine
  Entscheidung für Tobias.

### B4 (Mittel, Hardware-Prüfung) `gpioget` ohne Bias, falsche Syntax je nach libgpiod-Version, Prozessstart alle 0,2 s

* **Wo:** `headphones.py:70-81`, `config.py` (`intervall_s = 0.2`).
* **Szenario:**
  1. Das Docstring von `GpioKopfhoerer` und die Vorgabe `aktiv_niedrig=True` nehmen einen Pull-up an. `gpioget` wird ohne
     `--bias=pull-up` gestartet. Die Pins 9 bis 27 sind beim Pi-Start Pull-down. Ein offener Öffner-Kontakt läge dann auf „niedrig“
     und würde als „Stecker steckt“ gelesen.
  2. Der Aufruf `gpioget <chip> <pin>` ist die Syntax von libgpiod 1.x. `parse_pegel` versteht aber auch das Ausgabeformat von 2.x
     (`"17"=active`). In 2.x heißt der Aufruf `gpioget -c <chip> <pin>`, der alte Aufruf schlägt dort fehl. Das Modul unterstützt
     also nur eine der beiden Versionen, obwohl es beide zu können vorgibt.
  3. Ein Prozessstart fünfmal je Sekunde dauerhaft auf einem Pi 3A+ ist unnötige Last.
* **Vorschlag:** Bias ausdrücklich setzen (oder auf `gpiozero.DigitalInputDevice` wechseln, wie bei den Tasten). Die libgpiod-Version
  festlegen und im Test prüfen. Das Docstring sagt selbst „auf dem Pi zu prüfen“, daher als Prüfpunkt für Tobias aufnehmen.

### B5 (Mittel, Design-Frage) Liegende Karte hält die Box nachts an

* **Wo:** `idle.py:94-96` (`belegt` = spielt, `figur_liegt` oder `unbekannt`), `idle.py:10-12`.
* **Szenario:** Gute Nacht ist abgelaufen oder ein „stumm“-Fenster hat pausiert. Der Tobie oder die Gute-Nacht-Karte liegt noch.
  `figur_liegt` bleibt wahr, `idle` ist `aktiv`, der 20-min-Zähler läuft nie. Die Box bleibt die ganze Nacht an, bis zum Tiefstand
  bei 5 %. Das ist wörtlich die Tabelle („keine Wiedergabe **und** kein Tobie“), aber im Kern-Anwendungsfall Gute Nacht ist es
  vermutlich nicht gewollt (Akku am Morgen leer).
* **Vorschlag:** Tobias fragen. Möglich: Zähler startet auch bei „pausiert mit liegendem Tobie“ (nach der Pause, mit 20 min), oder
  nach `GuteNachtEnde` ein eigener Zähler.

### B6 (Niedrig bis Mittel) Zeitgesteuerter Sync läuft am Kern vorbei, auch nach dem Entschluss zum Herunterfahren

* **Wo:** `app.py:446-449` (`await self.sync.takt()` bei jedem `Takt`), `sync.py:216-223`.
* **Szenario:** `Sync.takt` fragt weder `idle` noch den Kern. Nach `Hauptknopf lang` (Zustand `herunterfahren`) und vor dem Ende des
  Dienstes kann ein fälliger Takt-Sync noch starten (Regel 6.2.1 filtert nur `SyncStarten` aus derselben Ausgabe). Am Mac, wo
  Herunterfahren nur protokolliert wird, startet er später beliebig. Beim ersten Eintritt in `home` ist `letzter_start = None`, der
  Sync beginnt also sofort.
* **Vorschlag:** `sync.takt()` nur, wenn `kern.teil["idle"].modus != "herunterfahren"`. Dazu ein Test.

### B7 (Niedrig bis Mittel) Start-Sync am Lader geht verloren, wenn die Netz-Klasse noch unbekannt ist

* **Wo:** `sync.py:207-210` (jede verbotene Lage heißt `SyncAbgebrochen("regel")`, auch „Netz noch nie gemessen“), `idle.py:157-167`,
  `app.py:822-825` (`netz.lauf` und `_strom_lauf` starten gleichzeitig).
* **Szenario:** `LaderGeaendert(True)` kommt vor der ersten `NetzKlasse` (nmcli und NAS-Probe dauern länger als der lokale PiSugar-Aufruf).
  `SyncStarten("start_lader")` trifft ein `Sync` mit `_netz = None`. Antwort `regel`, `idle` plant die Wiederholung erst in 10 min.
* **Beleg (`test_probe_race.py`):** Mit `[netz]`, `[strom]`, `[sync]` und Lader zuerst steht `wdh_bei = mono + 600` und
  `status.sync.grund == "regel"`.
* **Folge:** Der Start-Sync verzögert sich um 10 min, und die Box bleibt so lange an (gewollte Wiederholung, aber vermeidbar).
* **Vorschlag:** Beim Start zuerst auf die erste `NetzKlasse` warten (oder `idle` den Start erst nach `NetzKlasse` und `LaderGeaendert`
  auslösen). Ein App-Test mit echtem `Sync` für diese Reihenfolge ergänzen.

### B8 (Niedrig) `sim time`: Überlauf bei Extremwerten legt den Kern bei jedem Takt lahm

* **Wo:** `sim.py:365` (`dt.astimezone().timestamp()`, kein Schutz), `quiet.py:113-115` und `quiet.py:74-85` (Datumsrechnung).
* **Szenario:** `tobibox sim time 9999-12-31T23:59:59+00:00` (oder Jahr 1). `quiet.wirkung_jetzt` wirft `OverflowError`. Der Kern verwirft
  jeden `Takt` (`app.py:450-452` loggt `kern_ausnahme` alle 0,1 s). Der Zeiger wird nicht mehr periodisch gespeichert, `idle` zählt
  nicht. Jahr 1 ohne Zone: `astimezone()` wirft `ValueError`. Das ist kein `Ungueltig`, und `sim.py:420-441` (`_client`) fängt es nicht,
  die Verbindung bricht ohne Antwort ab.
* **Beleg (`probe2.py`):** `quiet wirft OverflowError` für Jahr 1 und Jahr 9999.
* **Vorschlag:** In `Sim._zeit` den Wertebereich begrenzen (z. B. 2000 bis 2100) und alle Ausnahmen in `Ungueltig` umwandeln. In
  `_client` ein `except Exception` mit Antwort `fehler`.

### B9 (Niedrig) `sim time` wirkt auch auf dem Pi

* **Wo:** `app.py:267` (`self.sim.zeit_haken = self._sim_zeit` immer), `app.py:285-294`.
* **Szenario:** Auf dem Pi stellt `tobibox sim time` die Wanduhr des Dienstes, ohne dass `[netz]`/`[strom]` auf `sim` stehen. Das wirkt
  auf Leise-Zeiten, Ablaufzeit von HA-Befehlen, Lesezeichen-Alter und auf `wall` im `resume.json`. Zugriff nur mit den Rechten des
  Dienst-Benutzers (`sim.sock` 0600), aber es ist ein unnötiger Schalter am Produktivgerät. Dasselbe gilt für `sim key`, `sim headphones`.
* **Vorschlag:** `zeit_haken` nur setzen, wenn die Zeitquelle `system` ist (Mac). Oder eine Konfigurationsoption, `sim.sock` auf dem Pi
  ganz auszulassen.

### B10 (Niedrig) Blockierende Dateizugriffe im Ereignisloop

* **Wo:** `sync.py:285-287` und `sync.py:361-368` (`mkdir`, `stat`, `os.walk(self.medien)` in `_zaehle_dateien`), `app.py:502`
  (`lauf.loesche` im Ausführer).
* **Szenario:** `os.walk` über den Medienordner auf der SD-Karte (tausende Dateien) läuft im Loop. Takt, Player-Ereignisse und Ring
  stehen so lange. Kurz, aber bei jedem Sync.
* **Vorschlag:** `_zaehle_dateien` und `_bereite_partial_vor` mit `asyncio.to_thread`.

### B11 (Niedrig) Ausnahme nach `core.step` verliert Befehle

* **Wo:** `app.py:355-368`.
* **Szenario:** `self.kern` wird in Zeile 355 gesetzt. Wirft danach `_ton_pegel_nachfuehren`, `_nachfuehren_stufe_4` (`led`,
  `bedienung`) oder `ausgang.nach_kern`, geht die Befehlsliste dieses Schritts verloren, der Kern-Zustand ist aber schon weiter
  (z. B. `spielt` ohne `Abspielen`, oder `herunterfahren` ohne `Herunterfahren`). Heute sind diese Aufrufe einfach, aber die
  Reihenfolge ist fragil.
* **Vorschlag:** Die Nachführungen in ein `try/except` mit Log, oder erst nach dem Einstellen der Befehle.

### B12 (Niedrig) Der Ton `akku_leer` wird nie ausgegeben

* **Wo:** `core.py:44` (nur in der Stumm-Liste), `idle.py:241-248` (`AkkuTiefstand` gibt keinen `TonSpielen`).
* **Szenario:** Bei Tiefstand schaltet die Box ohne Ton ab. Der Ton ist im Vertrag (`core-interface.md:297`) und als Datei vorgesehen,
  hat aber keinen Auslöser. Der Ring blinkt rot (`led.py:230`), der Ton fehlt.
* **Vorschlag:** Entscheiden, ob `idle` ihn ausgeben soll (Rang 6 vor `Herunterfahren`, Ton läuft nicht zu Ende, weil `poweroff`
  sofort kommt). Sonst im Vertrag streichen.

### B13 (Niedrig) Töne können in der „leiser“-Absenkung über der aktuellen Grenze klingen

* **Wo:** `app.py:407-414` (`dauerhaft` ohne `ausblenden` und `gute_nacht`), `quiet.py:186-189` (die Absenkung nutzt die Grenze
  `ausblenden`).
* **Szenario:** Beginnt ein „leiser“-Fenster bei lauter Wiedergabe, sinkt `ausblenden` drei Sekunden lang. `leise_zeit` wird erst
  am Ende der Rampe gesetzt. Ein Ton in diesen 3 s spielt mit der alten dauerhaften Grenze, also über der aktuellen wirksamen
  Grenze. Entscheidung J/B2 nimmt die Rampen `ausblenden` und `gute_nacht` bewusst aus (dort ist es sinnvoll, sonst wären Töne nach
  dem Ausblenden unhörbar), nennt aber nur Gute Nacht und „stumm“, nicht die Absenkung von „leiser“.
* **Vorschlag:** Im Vertrag (8.1) ergänzen. Oder `quiet` setzt `leise_zeit` sofort und rampt nur die Wiedergabe.

### B14 (Niedrig, nur Simulation) Kern senkt den Wunsch beim Hochdrehen unter einer Grenze

* **Wo:** `core.py:203-204` (`wunsch = min(wunsch + delta, wirksame_grenze)`).
* **Szenario:** Wunsch 40, Kopfhörer-Grenze 25, `sim regler +2`: Wunsch wird 25 (nicht 42). `Bedienung.drehen` an der echten Hardware
  sendet dagegen kein Ereignis (`controls.py:297-298`), Wunsch bleibt 40. Danach klingt die Box nach dem Ziehen unterschiedlich laut.
  Ungefährlich (nie lauter), aber Sim und Hardware weichen ab.
* **Beleg (`probe1.py`):** `dreh: [] 25`.
* **Vorschlag:** Entweder im Kern `max(wunsch, …)`-Seite anpassen (Hochdrehen über die Grenze ändert den Wunsch nicht) oder den
  Sim-Pfad über `Bedienung` leiten.

### B15 (Niedrig) Pi ohne `[netz]` und `[strom]` vertraut der Systemuhr

* **Wo:** `app.py:207-211`, `clock.py:23-28`.
* **Szenario:** Fehlen beide Abschnitte, ist `zeitquelle = None` und `SystemUhr` gilt als `system`/`zeit_ok`. Auf einem Pi ohne
  RTC und NTP stehen Leise-Zeiten dann auf einer falschen Uhr, und „stumm“ greift zur falschen Zeit. Das ist Konfiguration, aber es
  gibt keine Warnung.
* **Vorschlag:** Eine Warnzeile beim Start, wenn `leser.geraet != "sim"` und kein `[netz]`/`[strom]` da ist.

### B16 (Niedrig) `UpdateStarten` wird ohne Antwort verworfen

* **Wo:** `app.py:521-522`.
* **Szenario:** Der HA-Knopf „Update“ führt zu `UpdateStarten`. `app` loggt nur `befehl_nicht_umgesetzt` (DEBUG). HA sieht weder
  `befehl_abgelehnt` noch `UpdateGestartet`. Gehört zu Stufe 3b, sollte aber bis dahin eine ehrliche Ablehnung geben.
* **Vorschlag:** Bis 3b `EreignisSenden("befehl_abgelehnt", grund="bedingung", detail="Update noch nicht eingerichtet")`.

### B17 (Niedrig) `GpioTreiber.start` räumt bei Teilfehler nicht auf

* **Wo:** `controls.py:338-357`.
* **Szenario:** Wirft `RotaryEncoder` oder der dritte `Button` (Pin belegt), bleiben die schon erzeugten Geräte offen, weil
  `self.geraete` erst am Ende gesetzt wird. `stop()` kann sie nicht schließen. Beim Neustart des Dienstes im selben Prozess nicht
  relevant, aber sauberer wäre ein Aufräumen im `except`.

---

## Tests

* **T1 (Mittel) Die CUJ-Tests 14 bis 19 laufen nicht durch die echte Verdrahtung.** `tests/cuj/*` benutzen `CujBox` und `Stufe4Box`
  (`tests/conftest.py:358`, `tests/fixtures/stufe4.py:100-125`). Das ist der Kern mit `SimPlayer`. `Stufe4Box._fuehre_nach`
  ist eine **Kopie** von `App._nachfuehren_stufe_4` und `App._led_ausblenden`. Ändert jemand `app.py`, bleiben die CUJ-Tests grün.
  Die echte `App` prüfen nur `tests/unit/test_app_stufe4.py` und `tests/integration/test_stufe4_gui.py` und das mit Attrappen für
  `power.fuehre_aus` (`test_hauptknopf_lang_geht_als_herunterfahren_an_power`).
  Vorschlag: Die Nachführung aus `App` in eine Funktion ziehen, die `Stufe4Box` aufruft, statt sie zu kopieren.
* **T2 (Mittel) Es fehlen Tests für:**
  * Poweroff schlägt fehl und die Box schaltet danach doch noch ab (B1).
  * `Power.taste` im laufenden Dienst (B2).
  * Takt-Sync nach `Herunterfahren` (B6).
  * Start-Sync am Lader mit echtem `Sync` und unbekannter Netz-Klasse (B7). `test_start_am_lader_wiederholt_den_sync_ohne_sync_abschnitt_nicht`
    prüft nur den Fall ohne `[sync]`.
  * Kopfhörer nicht lesbar beim Start (B3).
  * `sim time` mit Extremwerten (B8).
* **T3 (Niedrig)** `tests/unit/test_app_stufe4.py::test_drehregler_aus_einem_thread_kommt_in_die_ereignisschleife` hat zwar
  `d.warte(...)`, aber kein eigenes `assert`. Es schlägt nur durch Zeitüberschreitung in `warte_bis` fehl. Das genügt, ist aber
  ohne `assert` leicht zu übersehen.
* **T4 (Niedrig)** CUJ 10 (Update) hat keinen Test. Stufe 3b, kein Code. Nur zur Erinnerung.
* **T5 (Niedrig)** Mehrere Test-Hilfen ersetzen `a.toene.spiele` und `a.player` (`fixtures/dienst.py:155`). Die Töne-Pegel prüft
  `tests/unit/test_app.py:421-471` mit echtem `Toene`. Dort ist es abgedeckt, in den Stufe-4-Tests nicht.

---

## Geprüft, ohne Befund

**Nichts startet von selbst**
* „stumm“ endet (`session.py:884-888`): nur `StummEndet`, `gehalten` wird `pausiert`. Test `test_konflikte.py:220`.
* Gute Nacht endet (`session.py:891-894`): nur Pause und Zeiger. Abheben im Ausblenden pausiert, Regel 7 hält die Lautstärke niedrig.
* Kopfhörer stecken oder ziehen in `pausiert`, `beendet`, `gehalten`: nur Grenze und Ausgang, kein `Abspielen` (`session.py:789-795`,
  Probe `probe1.py`).
* Sync endet (`SyncFertig`): nur Bibliothek neu laden (`app.py:392-393`), `session._bibliothek` speichert nur die Serien.
* Netz- und Stromwechsel gehen nur an `idle`, `sync`, `led`, Status. `LaderGeaendert` kann nur `SyncStarten` auslösen.
* Uhr gestellt (`sim zeit`, `ZeitquelleGeaendert`): `quiet` gibt höchstens `StummBeginnt` und `StummEndet` aus, nichts startet.
* HA-Konfiguration: `KonfigGeladen` startet bei liegendem Tobie nur nach 9.14 (CUJ 7a, Vertrag), nicht bei `gehalten`, `unbekannt`,
  `leer`, und unter „stumm“ nur mit Hinweiston.

**Grenzen und Lautstärke**
* Regel 6.2.7 für `ausblenden` und `gute_nacht` in `core.py:246`, auch beim Pausieren durch die Stumm-Rampe und beim Abheben im Ausblenden.
* Kopfhörerwechsel: erst Grenze (Rang 1), dann Ausgang (Rang 2). Die Lautstärke springt beim Ziehen im Spiel nach oben auf die
  Lautsprecher-Grenze. Das ist im Vertrag (CUJ 17) so festgelegt, kein Befund.
* `GeraeteEinstellungen` klemmt (`core.py:192-201`). `config.py` prüft `start` und `kopfhoerer` gegen `max` (Fehler statt stilles Kappen).
* `sounds.pegel`: `min(grenze, …)` ist immer der letzte Schritt, auch bei `hinweis`.
* `Bedienung.drehen` geht nie über die Grenze, der Kern klemmt zusätzlich.

**Herunterfahren und Leerlauf**
* Reihenfolge der Befehle: `Pausieren` (3), `ZeigerSpeichern` (4), `Herunterfahren` (10), serieller Ausführer, `to_thread` wird abgewartet.
* Regel 6.2.1 entfernt `Abspielen`, `SyncStarten`, `UpdateStarten`, `AusgangWaehlen` in derselben Ausgabe.
* Lernmodus, Sync, Update, offener Sync (höchstens 60 s) und Wiederholung blockieren die Abschaltung. Nie hängend außer B1.
  Endet der Lernmodus, beginnt der Zähler neu. Die Wiederholung endet bei Lader weg, 6 Versuchen, anderem Grund.
* Tiefstand: Sync wird abgebrochen und es wird heruntergefahren. Lader bekannt gilt als Voraussetzung (`power._tiefstand_pruefen`).

**asyncio**
* Dauerläufe fangen Ausnahmen: `_led_lauf`, `Buchse.lauf`, `Netz.lauf`, `Power.lauf`, `_strom_lauf` (Start), `Ha._verarbeiter`,
  `Ha._status_schleife`, `_ausfuehrer`, `_ereignisschleife`.
* `_raeume_auf` bricht alle Aufgaben ab (auch `_hintergrund`, `Start`), beendet rsync mit SIGTERM und danach SIGKILL nach 10 s, jeder
  Schritt mit Zeitgrenze. Ein neuer Sync nach dem Beenden ist durch das Abbrechen der Takt-Aufgabe ausgeschlossen.
* Kein `subprocess.run`, `time.sleep`, kein blockierendes Netz auf dem Loop (`gpioget`, `nmcli`, `timedatectl`, PiSugar-TCP, rsync
  sind alle `asyncio` mit Frist). Ausnahme B10.
* gpiozero-Rückrufe gehen über `call_soon_threadsafe` (`app.py:269-277`). MQTT-Rückrufe über `Ha._von_netz` ebenso.

**Konfiguration**
* Ohne `[mqtt]`, `[netz]`, `[strom]`, `[sync]` läuft die Box am Mac (HA-Ersatz, `sim` gibt die Ereignisse selbst aus). `[tasten]` und
  `[kopfhoerer]` haben die Vorgabe `sim`.
* Pi-Werte am Mac: `gpio` ohne `gpiozero` ist `ImportError` und wird gefangen (`app.py:831-837`). `gpioget` fehlt: `OSError`, gefangen.
  `nmcli` fehlt: Netz `offline` mit einer Warnung. PiSugar nicht erreichbar: `PiSugarFehler`, gefangen.
* Unbekannte Schlüssel geben nur eine Warnung (Rückfall nach Update).

**Sicherheit**
* MQTT-Passwort: `MqttKonfig.passwort` hat `repr=False`, `eventlog._GEHEIM` schwärzt, Status und `tobibox status` zeigen nur
  `box_id@host:port`. Sync-Passwort nur per Datei oder Umgebung des Kindprozesses, nie in der Befehlszeile oder im Protokoll.
* GUI: nur `127.0.0.1`, kein `--host`, `Host`-Prüfung (DNS-Rebinding), `Origin`-Prüfung, `POST` nur mit `application/json`, kein
  `OPTIONS`, `ERLAUBT`-Liste ohne `zeit`, Körper höchstens 16 KiB, Zeitlimit 10 s. Die Seite benutzt nur `textContent`, kein
  `innerHTML`.
* `sim.sock`: erst `bind`, dann `chmod 0600`, dann `listen`. Kein Pfad aus der Eingabe, Befehle über feste Tabellen. `card` prüft über
  `ha_ersatz.schreibe_zuordnung`.
* Themen: `uid_aus_ack` lässt `/`, `+`, `#` nicht zu.

**Tests**
* 2763 bestanden (`tests/unit`, `tests/cuj`). Die Integrationstests mit Mosquitto, MPD und rsync wurden nicht gelaufen
  (brauchen Dienste, überspringen sich sonst).
* Kein Test ohne Behauptung außer T3. Keine `skip`/`xfail` im neuen Code außer den Dienst-Voraussetzungen.

---

## Auflösung (09.11., Rev. 3.17)

Neue Entscheidungen von Tobias: **O** (Leerlauf zählt auch mit liegendem Tobie, Befund B5) und **P** (nicht lesbarer Kopfhörer-Kontakt:
die Kopfhörer-Grenze gilt, Befund B3). Tests: `box/tests/unit/test_befunde_stufe3a_4.py` (neu) und die geänderten Tests in `test_idle.py`,
`test_headphones.py`, `cuj/test_cuj16_leerlauf.py`.

| Befund | Ergebnis |
|---|---|
| B1 (hoch) | **Behoben.** `power` prüft Rückgabecode, fehlendes Kommando und Frist (60 s) und sendet `HerunterfahrenFehlgeschlagen`; `idle` verlässt `herunterfahren`, zählt neu, schreibt ins Protokoll und meldet HA `fehler`/`herunterfahren_fehlgeschlagen`. Ein fortbestehender Tiefstand wird nach 60 s wieder gemeldet. Marker `lauf.json` wird wieder geschrieben. Mac und ohne `[strom]`: nur protokolliert, `idle` kehrt nach 10 s zurück (`SIMULATION_RUECKKEHR_S`, im Vertrag). |
| B2 | **Behoben mit Vorbehalt (am Pi prüfen).** Recherche: Für den `pisugar-server` ist kein Befehl für Tastenereignisse belegt. Die Abfrage `power.taste_lauf` steht hinter `[strom] taste_befehl` (Vorgabe aus, im Code und in `docs/betrieb/pisugar-wecker.md` als „am Pi prüfen“ markiert). Ohne `taste_befehl` und `pin_haupt` warnt der Dienst beim Start. Offener Punkt im Plan (3.2.4). |
| B3 | **Behoben (Entscheidung P).** Neues Ereignis `KopfhoererLesbar`; `session` hält die Kopfhörer-Grenze, solange der Kontakt nicht lesbar ist (auch beim Start), der Ausgang bleibt; HA bekommt `fehler`/`kopfhoerer_unlesbar`. Wieder lesbar erst nach einem stabilen Wert. |
| B4 | **Behoben (am Pi prüfen).** Vorrang `gpiozero.DigitalInputDevice` (Pull-up ausdrücklich, kein Prozess je Messung, unabhängig von libgpiod, dieselbe Bibliothek wie die Tasten). Rückfall `gpioget --bias=pull-up|pull-down` mit erkannter Version (1.x `gpioget <chip> <pin>`, 2.x `gpioget -c <chip> <pin>`), dann höchstens 1 Messung je Sekunde. |
| B5 | **Behoben (Entscheidung O).** `belegt` ist nur noch `spielt` oder `unbekannt`. Folge: Der Ring zeigt die Pause auch im Leerlauf mit liegendem Tobie weiter und kein Aufwachen-Lauflicht beim Weiterspielen (`led.py`). |
| B6 | **Behoben.** Kein zeitgesteuerter Sync, wenn `idle` in `herunterfahren` steht. |
| B7 | **Behoben.** Start-Sync am Lader wartet (eigene Aufgabe, höchstens 30 s) auf die erste `NetzKlasse`; danach `sync.start`. Ohne Netz-Klasse nach der Frist antwortet `sync` wie bisher mit `regel` und `idle` wiederholt. |
| B8 | **Behoben.** `sim time` nimmt nur Jahre 2000 bis 2100; Überlauf und Haken-Fehler werden zu `iso ungueltig`; `_client` fängt jede Ausnahme (`intern`); `quiet.wirkung_jetzt` behandelt eine Uhr außerhalb des Bereichs wie eine unsichere Uhr (nie „stumm“). |
| B9 | **Behoben.** `[sim] erlauben` (Vorgabe aus). `sim` bedient Tasten, Regler, Kopfhörer, Strom, Netz, Zeit und den HA-Ersatz nur mit Quelle `sim`; sonst `quelle_nicht_sim`. `anzeige` nennt `quelle_sim`, die Seite graut aus. Die Tobies (`tobie_*`) bleiben immer erlaubt (echter Leser parallel am Mac). |
| B10 | **Behoben.** `_zaehle_dateien`, `mkdir` und `_bereite_partial_vor` des Syncs und `lauf.loesche` laufen mit `to_thread`. |
| B11 | **Behoben.** Alle Nachführungen nach `core.step` laufen einzeln abgesichert; Befehle werden immer eingereiht. |
| B12 | **Behoben.** `idle` gibt bei `AkkuTiefstand` einmal `TonSpielen("akku_leer")` aus; der Dienst wartet vor dem Poweroff bis zu 5 s auf das Ende des Tons. |
| B13 | **Behoben.** `nachfuehrung.ton_pegel` rechnet während der „leiser“-Absenkung schon mit deren Ziel (im Vertrag, 8.1). |
| B14 | **Behoben.** `sim regler` geht über `Bedienung.drehen_prozent` wie der Drehregler; das Verhalten des Kerns bleibt nach Vertrag. |
| B15 | **Behoben.** Linux mit echter Systemuhr und ohne `[netz]`/`[strom]`: Zeit unsicher, bis `/run/systemd/timesync/synchronized` oder `timedatectl` NTP melden (alle 10 s); Warnung beim Start. Am Mac (und mit Test-Uhr) weiter sicher. `sim time` ist dort gesperrt. |
| B16 | **Behoben.** `UpdateStarten` wird mit `befehl_abgelehnt` (`detail` „Update kommt mit Stufe 3b.“) beantwortet. |
| B17 | **Behoben.** `GpioTreiber.start` schließt bei einem Teilfehler alle schon erzeugten Geräte. |
| T1 | **Behoben.** Neues Modul `box/src/tobibox/nachfuehrung.py` (wie `ausgang.py`): `App` und `BedienBox` (CUJ 14 bis 19) rufen denselben Code; die Kopie ist weg. |
| T2 | **Behoben.** Neue Tests zu B1 bis B17 in `tests/unit/test_befunde_stufe3a_4.py`, dazu Idle- und CUJ-16-Tests zu O. |
| T3 | **Behoben.** `assert` ergänzt. |
| T4, T5 | Nicht Teil dieses Auftrags (Stufe 3b bzw. niedrig). |
| GUI-Ring | **Behoben.** Farbe normiert (volle Deckkraft), echte Helligkeit als Zahl und Balken (Marke = Deckel 25 %). Der Deckel der Box ist unverändert. |

**Am Pi zu prüfen:** (1) wie der `pisugar-server` die Taste meldet (B2, Befehl und Antwortwort für `taste_befehl`); (2) gpiozero-Lesen des
Schaltkontakts und Pegel (`aktiv_niedrig`, Pin) sowie Rückfall `gpioget` mit installierter libgpiod-Version (B4); (3) Rückgabecode und
Dauer von `systemctl poweroff` mit dem Dienstbenutzer (Rechte, polkit; B1); (4) `/run/systemd/timesync/synchronized` unter dem
verwendeten NTP-Dienst (B15); (5) Ton `akku_leer` ist nur ein Platzhalter (Datei vorhanden?).
