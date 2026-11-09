# PiSugar: Anbindung und nächtlicher Wecker (nur Beschreibung)

Stand: 09.11. (AP 4.3). Dieses Dokument beschreibt, wie die Box mit dem PiSugar
spricht und wie sie nachts am Lader zum Sync geweckt werden könnte. Es ist
**keine Anleitung zum Einrichten**. Der Wecker wird erst gebaut, wenn Tobias
es entscheidet (Abschnitt 5). Gebaut ist der Wecker nicht, es gibt dafür
keinen Code.

Quellen sind die README des Projekts `PiSugar/pisugar-power-manager-rs` und die
PiSugar-Wiki (Stand der Recherche 09.11.). Was dort **nicht** steht, ist unten
als „am Gerät prüfen“ markiert.

## 1. Wie die Box mit dem PiSugar spricht

Auf dem Pi läuft der Dienst `pisugar-server`. Das Modul `power.py` fragt ihn
über TCP auf `127.0.0.1:8423` (Einstellungen `[strom] pisugar_host` und
`pisugar_port`). Jede Frage ist eine Textzeile, die Antwort ist eine Zeile der
Form `name: wert`. Beispiel von Hand:

```
echo "get battery" | nc -q 0 127.0.0.1 8423
```

Der Server kennt vier Wege: TCP (8423), Unix-Socket
(`/tmp/pisugar-server.sock`), WebSocket (8422) und HTTP (8421). Nur HTTP
verlangt eine Anmeldung (Standard `admin`/`admin` in
`/etc/pisugar/config.json`); TCP und Socket nicht. Die vollständige
Befehlsliste liefert der Server selbst auf die Anfrage `help xx`.

## 2. Die Befehle, die `power.py` benutzt

| Befehl in `power.py` | Bestätigt? | Antwort laut Quelle | Anmerkung |
|---|---|---|---|
| `get battery` | ja | `battery: <Zahl>` (Prozent, Kommazahl) | Passt zu `parse_antwort`. |
| `get battery_power_plugged` | ja, nur neue Modelle | `battery_power_plugged: true\|false` | Der PiSugar 3 gehört zu den neuen Modellen. Genau das Richtige für „Netzteil steckt“. |
| `get battery_charging` | ja | `battery_charging: true\|false` | Für neue Modelle ausdrücklich nicht empfohlen (nimm `battery_power_plugged`). Der Rückfall in `power.py` ist harmlos. |
| `get rtc_time` | ja | `rtc_time: <ISO-8601-Zeit>` | Mit Zeitzone. Passt zu `parse_rtc`. |
| `rtc_rtc2pi` | ja | in der Quelle keine Antwort angegeben | Setzt die Systemuhr aus der RTC. Siehe Abschnitt 3. |

Weitere Befehle, die für den Wecker wichtig wären:

| Befehl | Wirkung |
|---|---|
| `rtc_pi2rtc` | Systemzeit in die RTC schreiben. |
| `rtc_alarm_set <ISO-Zeit> <repeat>` | Weckzeit setzen. Beispiel der Quelle: `rtc_alarm_set 2020-06-26T16:09:34+08:00 127`. |
| `rtc_alarm_disable` | Wecker ausschalten. |
| `get rtc_alarm_enabled` | `rtc_alarm_enabled: true\|false` |
| `get rtc_alarm_time` | `rtc_alarm_time: <ISO-Zeit>` |
| `set_button_enable <single\|double\|long> <0\|1>` | Tastenaktion ein- oder ausschalten. |
| `get safe_shutdown_level` / `get safe_shutdown_delay` | Akkustand und Wartezeit für das sichere Herunterfahren des PiSugar. |

## 3. Befunde zu `power.py`

Die vier Befehle aus dem Gedächtnis sind **richtig geschrieben** und kommen in
der Quelle vor. Abweichungen gibt es nicht bei den Namen. Offen sind zwei
Punkte, beide nur am Gerät zu klären:

1. **Antwort auf `rtc_rtc2pi`.** Die Quelle gibt keine Antwortzeile an.
   `PiSugarStrom._frage` erwartet genau eine Zeile und wirft einen Fehler
   (`PiSugarFehler`), wenn der Server die Verbindung ohne Antwort schließt.
   Der Fehler fängt `Power.start` ab und schreibt nur eine Warnung ins
   Protokoll. Dann bleibt aber die Systemuhr unverändert, obwohl der Befehl
   vielleicht gewirkt hat. Am Pi prüfen: `echo "rtc_rtc2pi" | nc -q 1 127.0.0.1 8423`.
2. **Antwortname bei `get battery_power_plugged`.** Die Quelle nennt den Namen
   in der Antwort gleich dem Namen im Befehl. `parse_antwort` prüft genau das.
   Antwortet die installierte Version anders, wirft `lader()` einen Fehler
   und `Power.pruefe` meldet keinen Lader. Der Sync im Hotspot (Lader oder
   Akku über 50 %) und die Lader-Regel der Abschaltung fallen dann auf
   „unbekannt“ zurück, also auf die vorsichtige Seite.

Ein Sicherheitshinweis: Der Server hört nach der Quelle auf `0.0.0.0:8423`,
also auf allen Netzen. Auf der Box sollte er nur auf `127.0.0.1` hören. Das
steht in `/etc/pisugar/config.json` (Schlüssel für die Adresse am Gerät
nachsehen). Die Box selbst ist über Tailscale im Netz, eine offene
Strom-Schnittstelle gehört nicht dazu.

Die Tasten (Einfach, Doppel, Lang) führt der PiSugar als Shell-Befehle aus,
siehe `docs/plan/stueckliste-und-psp.md`, Punkt 4. Sie laufen nicht über
diese TCP-Befehle.

## 3a. Hauptknopf: Wie kommt die Taste zur Box? (Review B2, 09.11., **am Pi prüfen**)

Das Modul `power.py` hat eine Methode `taste(art)`, die ein `Hauptknopf`-Ereignis (kurz oder lang) in den Kern gibt. Nur gab es im
Dienst keinen, der sie aufruft. Die Recherche (README `PiSugar/pisugar-power-manager-rs`, Stand 09.11.) ergibt:

- Der `pisugar-server` kennt `get button_enable`, `set_button_enable <single|double|long> <0|1>` und `get button_shell`. Die Tasten
  führen **Shell-Befehle** aus (Plan, Punkt 4).
- Es ist **kein** Befehl belegt, der ein Tastenereignis meldet (weder Abfrage noch Abonnement, auch nicht über WebSocket 8422 oder
  HTTP). Die Namen der Konfigurationsschlüssel für die Shell-Befehle in `/etc/pisugar-server/config.json` sind in der Quelle nicht
  sicher belegt.

Deshalb ist der Weg in der Box **hinter einer Einstellung** und standardmäßig aus:

```toml
[strom]
quelle = "pisugar"
# taste_befehl = "get button_event"   # PLATZHALTER, am Pi prüfen: Befehl, dessen Antwort die Taste nennt
# taste_intervall_s = 0.5
```

`power.taste_lauf` schickt `taste_befehl` alle `taste_intervall_s` an den `pisugar-server` und versteht in der Antwortzeile
(`name: wert`) die Werte `long`/`lang` (Hauptknopf lang) und `single`/`short`/`kurz` (Hauptknopf kurz). **Am Pi zu prüfen:** Gibt es
überhaupt so einen Befehl (`help xx` am Server fragen), und wie heißt die Antwort? Passt sie nicht, bleibt die Taste stumm; dann muss
`parse_taste` in `power.py` angepasst werden.

Zwei sichere Wege ohne diese Abfrage:

1. **Knopf am GPIO:** Der Arcade-Knopf liegt nach Plan 3.2.4 parallel zum PiSugar-Taster. Hängt er zusätzlich an einem GPIO,
   steht `[tasten] pin_haupt` (dann kommt der Hauptknopf über `controls`).
2. **Shell-Befehl des PiSugar:** Der PiSugar ruft bei Einfach- und Langdruck einen Befehl auf (z. B. `tobibox sim key haupt`, wenn
   `[sim] erlauben = true` gesetzt ist). Das ist ein Behelf und noch nicht erprobt.

Fehlen `taste_befehl` **und** `pin_haupt` bei `[tasten] quelle = "gpio"`, schreibt der Dienst beim Start die Warnung
`hauptknopf`/`ohne_quelle` ins Protokoll: Dann gehen Pause, Weiter und Abschalten per Hauptknopf nicht.

## 4. Der Wecker: Idee und Ablauf

Ziel (CUJ 16, „Später kann der PiSugar-Wecker die Box am Lader nachts zum Sync
wecken“): Die Box ist nachts ausgeschaltet, am Lader. Der PiSugar schaltet sie
zu einer festen Uhrzeit ein, die Box synchronisiert und fährt wieder herunter.

Der Ablauf mit den Teilen, die es schon gibt:

1. Die Box fährt herunter (Leerlauf nach 20 min oder Hauptknopf lang).
2. Der PiSugar schaltet die Box zur Weckzeit ein (RTC-Alarm).
3. Beim Start liest `power.py` die RTC und setzt die Systemuhr (`rtc_rtc2pi`).
   Die Zeit gilt dann als vertrauenswürdig, wenn die RTC plausibel ist.
4. Der Kern bekommt `Bereit` und den Lader-Zustand. `idle.py` stößt am Lader
   genau einmal den Sync an (`SyncStarten("start_lader")`). Ob er läuft,
   entscheidet `sync` nach der Netz-Regel.
5. Während der Sync läuft, schaltet `idle.py` nie ab. Sobald er fertig ist
   und kein Tobie liegt, fährt die Box sofort herunter. Gab es keinen Sync zu
   tun, gilt die 20-Minuten-Regel.

Damit braucht die Box für den Wecker **keine neue Logik im Kern**. Es fehlt nur
das Setzen der Weckzeit.

### Was dazukommen müsste (nicht gebaut)

- **Weckzeit setzen:** Einmal am Gerät, oder bei jedem Start, ein Aufruf
  `rtc_alarm_set <Zeit mit Zeitzone> 127`. Der Wert `127` heißt laut Quelle
  „jeden Wochentag“ (`1111111`). Wie die Bits den Wochentagen zugeordnet sind,
  steht nicht in der Quelle. Für „jede Nacht“ reicht `127`.
- **Wo:** Am einfachsten ein kleiner Eintrag beim Herunterfahren, der die
  Weckzeit setzt (`abschalt_kommando` in `[strom]`), oder ein eigener
  Dienst-Schritt. Eine Entscheidung dafür gibt es noch nicht.
- **Uhr:** Die RTC muss stimmen. Dafür gibt es `rtc_pi2rtc`, solange die Box
  mit NTP-Zeit läuft.

### Am Gerät zu prüfen, bevor man sich darauf verlässt

- Schaltet der PiSugar 3 Plus die Box nach einem sauberen Herunterfahren
  durch den RTC-Alarm wieder ein? Die Wiki führt „Timing boot“ für die
  PiSugar-3-Reihe als unterstützt. Der genaue Ablauf (wie lange der PiSugar
  nach dem Herunterfahren die Spannung hält, was mit `auto_power_on` ist)
  steht nicht in der Quelle.
- Bleibt der Alarm nach dem Wecken gesetzt (wiederholend), oder muss er jedes
  Mal neu gesetzt werden?
- Wie viel Akku kostet das? Am Lader ist das egal, ohne Lader sollte die Box
  nicht wecken. Der Wecker ist nur für „am Lader“ gedacht.
- Reicht die Zeit zwischen Wecken und dem ersten Sync (WLAN, Tailscale)? Die
  Netz-Klasse kann beim Start noch `offline` sein; dann meldet `sync`
  `SyncAbgebrochen("netz_weg")`, und die Box fährt herunter, ohne es später
  noch einmal zu versuchen. Das ist eine Lücke im Entwurf (Abschnitt 6).

## 5. Entscheidung für Tobias

Ob der nächtliche Wecker gebaut wird, entscheidet Tobias nach dem Pi-Probelauf
mit dem PiSugar. Bis dahin gilt: Der Sync läuft auf den Takt im Dienst und auf
den HA-Knopf, solange die Box an ist, und beim Start am Lader.

Vor der Entscheidung zu klären:

1. Soll die Box nachts überhaupt am Lader stehen und ausgeschaltet sein? Oder
   steht sie tagsüber im Zimmer und läuft einfach?
2. Welche Uhrzeit? (Das Heim-WLAN und das NAS müssen dann an sein.)
3. Soll die Box nach dem Sync wirklich herunterfahren? Mit dem jetzigen
   `idle.py` tut sie das, sobald kein Tobie liegt.

## 6. Lücken, die beim Schreiben aufgefallen sind

- **Erledigt (Rev. 3.16 und 3.17):** Der Start-Sync am Lader wird alle 10 min bis zu 6-mal wiederholt und wartet beim Start auf die erste
  Netz-Klasse (höchstens 30 s). Die folgende Beschreibung ist der Stand vor dieser Änderung.
- **Kein zweiter Versuch beim Start-Sync.** Kommt `SyncAbgebrochen` mit
  `netz_weg` oder `regel`, wartet die Box nicht auf bessere Netzverhältnisse.
  Beim nächtlichen Wecker würde die Box dann herunterfahren, ohne
  synchronisiert zu haben. Mögliche Lösung (nach Entscheidung): ein paar
  Minuten auf die Netz-Klasse `home` warten, bevor `idle.py` aufgibt.
- **Lader unbekannt beim Start.** Meldet `power.py` den Lader nie (Fehler im
  `pisugar-server`), startet kein Sync beim Start. Das ist die vorsichtige
  Seite.
