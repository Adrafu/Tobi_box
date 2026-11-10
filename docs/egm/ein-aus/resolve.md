# Ein- und Ausschalten: Resolve (EGM Schritt 4)

Stand 10.11. · Grundlage: `design_draft.md` (Rev. 1), `review_software.md` (G1–G15), `review_hardware.md` (H-G1–H-G15).
Entscheidungen von Tobias sind mit **(Tobias)** markiert, technische Festlegungen der Projektleitung mit **(PL)**.

## 1. Entscheidungen von Tobias (10.11.)

| # | Frage | Entscheidung |
|---|---|---|
| R1 | Ring beim Hochfahren (G5, H-G15 B) | **Weiche in Hardware (Tobias).** Ein Chip mit Freigabe-Eingang (z. B. 74AHCT125) schaltet die Ring-Leitungen zwischen ESP32 und Pi um. Der ESP32 zeigt nur beim Wecken das weiße Lauflicht, bis der Pi übernimmt; danach steuert der Pi den Ring wie heute (`led.py` bleibt). Der ESP32 schaltet den Ring-MOSFET. Akku: fast gleich wie „ESP32 steuert immer“ (Unterschied unter 1 % am Tag). Der Befehl `RING` mit Mustern entfällt. |
| R2 | Sparsames Lauschen (LPCD) im Zustand Bereit (G3) | **Streichen (Tobias).** Ersparnis nur ~0,075 Wh am Tag. Der Leser fragt in Bereit normal ab. Light-Sleep später prüfen. LPCD bleibt für den Zustand Aus. Ersetzt E2. |
| R3 | Liegender Tobie nach dem Ausschalten (G1) | **Nur ein neu aufgelegter Tobie weckt (Tobias).** Ein Tobie, der seit dem Ausschalten unverändert liegt, weckt nie; Abheben und wieder Auflegen weckt; der Hauptknopf weckt immer. |
| R4 | Rückmeldung beim Andocken einer laufenden Box (G14) | **Eigener Lader-Ton (Tobias)**, kurz. Nicht in Leise-Zeiten (S5), nicht während ein Hörspiel spielt (S9: nur Ring). Nie zwei Töne zugleich (Entscheidung L). |
| R5 | Helligkeit des Lauflichts beim Wecken (G9) | **Tags normal, nachts gedimmt (Tobias).** Der Pi gibt dem ESP32 vor dem Ausschalten mit, bis wann gedimmt wird (Ende des aktuellen oder nächsten Leise-Fensters). Ohne gültige Angabe: gedimmt (sicherer Wert). |
| R6 | Magnetsensor für Tonies (H-G15 A, E12) | **Gleich mit einbauen (Tobias).** Ein sparsamer Hall-Schalter im Deckel ist zweite Weckquelle für Tonies (Magnet im Fuß; am Muster prüfen). NFC-Karten wecken nur über LPCD, sonst über den Hauptknopf. Für R3 gilt: Auch der Magnetsensor weckt nur bei einer Änderung. |
| R7 | Ruhestrom der SuperMini (H-G5) | **Löten ist in Ordnung (Tobias).** Erst messen; zieht sie zu viel, Power-LED ablöten oder Brücke trennen. |

## 2. Technische Festlegungen der Projektleitung

| # | Befund | Festlegung |
|---|---|---|
| P1 | Am Sockel nie aus (G2) | **`STROM_IN` ist Pflicht (PL):** Ein Teiler von der USB-C-Eingangsspannung an einen ESP32-Pin. Der ESP32 erkennt so Andocken selbst und weckt den Pi bei der Flanke; die Box hängt nicht mehr davon ab, wie „Einschalten bei Strom“ am PiSugar arbeitet. Der Pi bekommt den Wert über den Leser. „Strom unbekannt“ (keine Quelle antwortet) gilt nach 60 s als „kein Strom“. |
| P2 | Fehlimpuls an Pad 10 (H-G3, H-G4) | **(PL)** Der ESP32 drückt Pad 10 nur, wenn die 5 V des Pi sicher fehlen, und höchstens einmal je Wecken. Statt Anti-Mistouch abzuschalten, bildet er „kurz, dann lang“ nach, wenn die Messung das verlangt. Pulsbreiten am Muster messen. |
| P3 | Strom für das Lesefeld des PN5180 (H-G1) | **(PL)** Das Feld (TVDD) braucht eine feste Versorgung, auch wenn der Pi aus ist. Lösung hängt von der Leser-Platine ab: **Tobias nennt die verbaute PN5180-Platine** (Link oder Foto), dann Schaltplan lesen. Vorrang hat volle Reichweite (2,5 cm durch den Deckel); ein kleiner 5-V-Wandler aus dem Akku ist erlaubt, wenn nötig. |
| P4 | Rückspeisung über USB-Datenleitungen (H-G2) | **(PL)** Am Muster messen. Fließt Strom in den ausgeschalteten Pi, kommt ein USB-Schalter dazu, den der ESP32 erst bei anliegenden 5 V des Pi schließt. |
| P5 | Dienst-Neustart (G8) | **(PL)** Wie heute (Entscheidung G): Start-Ton bleibt, keine Lader-Rückmeldung, kein Wecken. Boot-Kennung trennt Einschalten von Dienst-Neustart. |
| P6 | Früher Start-Ton (G7, G8) | **(PL)** Der Frühton-Dienst darf den Box-Dienst nicht aufhalten (kein blockierendes `Before=`). „Nie zwei Töne“ wird über eine Datei unter `/run` und eine feste Reihenfolge gesichert, nicht über Zeitglück. |
| P7 | Hauptknopf auf dem Pi (G11, B2) | **(PL)** Am Pi messen, welcher Weg geht (pisugar-server-Befehl). Für das spätere Mitlesen durch den ESP32 wird nur der Teiler vorgesehen. |
| P8 | Verträge in zwei Schritten (G12) | **(PL)** Schritt 1 jetzt (nach Tobias' Freigabe): 10-min-Frist, am Strom immer bereit, Lader-Ton, Frühton, `STROM_IN`-Wert. Schritt 2 nach den Breadboard-Messungen: `WAKE`, `SLEEP`, LPCD, Magnetsensor, Weiche. |
| P9 | Zeitziele Lauflicht (H-G14) | **(PL)** So schnell, wie die Messung erlaubt; Ziel unter 1,5 s ab Wecken. |
| P10 | Akku leer, Wächter (H-G6) | **(PL)** Der Wächter darf bei leerem Akku mit der Unterspannung des Reglers ausgehen; den Akku schützt der PiSugar. |
| P11 | Pinplan (H-G11) | **(PL)** Neu planen: GPIO 3 ist Strapping-Pin; zusätzliche Funktionen (`STROM_IN`, Weiche, MOSFET, Pad 10, Hall, IRQ des PN5180) auf GPIO 14–18 und 21. Wecken aus dem Tiefschlaf nur über RTC-fähige Pins. |
| P12 | Vollständige Vertragsliste (G10) | **(PL)** Revision zählt alle Stellen neu, inkl. „Liste der Fehlercodes vollständig“, Konfigurationsschlüssel und Weg zum Flashen der Firmware. |

## 3. Was offen bleibt

- **Tobias:** Welche PN5180-Platine ist verbaut (P3)?
- **Breadboard/Muster:** die Messliste aus `design_draft.md` Abschnitt 10 und `review_hardware.md`, ergänzt um Hall-Schalter mit Tonie-Fuß, Rückspeisung über D+, TVDD und Reichweite.
- Noch nicht gefragt und unverändert als Vorschlag: E3 (Akku dauernd voll am Sockel), E4 (Neustart am Sockel nach Hauptknopf lang, durch `STROM_IN` entschärft), E9 (10-min-Frist ab Abziehen), E10 (ESP32 schaltet einen hängenden Start nach 120 s aus), E13 (Startziel 10 s, Rückfall 15 s), E14 (Frühton nur außerhalb der Leise-Zeiten).

## 4. Nächster Schritt

Design-Entwurf Rev. 2 mit allen Punkten oben. Danach Freigabe durch Tobias, dann Schritt 1 der Verträge und des Codes (am Mac in der Simulation prüfbar), parallel die Breadboard-Messungen.
