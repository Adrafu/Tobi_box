# Design: Ladestation (Dock) Tobi Box

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-09
* **Stand:** Draft, Abschnitte 1–4 geschrieben, 5–8 folgen
* **Grundlage:** `docs/egm/ladestation/concepts_brief.md` (Entscheidungen
  D1–D7), `docs/plan/stueckliste-und-psp.md`, `docs/designs/box-software.md`

Werte mit **(R)** sind Richtwerte und werden am Muster gemessen oder geprüft.

---

## 1. Ziel und Anforderungen

Jede Box hat einen eigenen Sockel. Ein Kind stellt die Box ab, auch im
Dunkeln und in beliebiger Drehung, und sie lädt. Sonst passiert nichts: Die
Box wacht nicht auf, nichts leuchtet am Sockel.

| # | Anforderung | Herkunft |
|---|---|---|
| A1 | Box lädt in jeder der vier Drehlagen. | D2 |
| A2 | Kind dockt blind an: Die Box findet über einen Fangtrichter selbst in Lage. | D1 |
| A3 | Kind hebt die Box einhändig ab, der Sockel bleibt stehen. | D1 |
| A4 | Ohne aufsitzende Box sind die Sockel-Kontakte spannungslos. | Plan 1.4 |
| A5 | Beim USB-C-Laden sind die Box-Kontakte spannungslos. | Punkt 7 |
| A6 | Münze oder Löffel auf Sockel oder Box richtet nichts an, auch nicht, wenn ein fremder Magnet den Reed auslöst. | PSP 3.5.4, 8.3.4 |
| A7 | Andocken weckt die Box nicht. | Punkt 3, PSP 8.2.4 |
| A8 | Je Sockel genug Strom, dass eine leere, laufende Box (Sync, Musik) noch lädt. | PSP 8.4.5 |
| A9 | Keine Magnete, Kleinteile oder Kontakte, die ein Kind herauslösen kann. | Punkte 13–15 |
| A10 | Kein Metall näher als 2–3 cm an der NFC-Antenne. | Punkt 10 |
| A11 | Keine Anzeige am Sockel. | D6 |
| A12 | Kein Signal vom Sockel zur Box. Die Box erkennt „am Lader“ selbst über den PiSugar. | box-software.md |

**Nicht Ziel:** Laderegelung im Sockel, Datenverbindung, Ladeanzeige am
Sockel, ein gemeinsames Netzteil für beide Boxen.

---

## 2. Aufbau im Überblick

```
 Steckdose                Sockel                              Box
 ─────────               ─────────────────────────────────    ──────────────────────
 USB-C-NT ──USB-C──► Breakout ─► PTC ─► Load-Switch ─► Mittel-Pin ═► Mittelfläche ─► #5398 Eing. A ─┐
 5 V / 3 A          (5,1 kΩ CC)          #2810   ▲                                                ├─► PiSugar 3 Plus
                                                 │ ON                       USB-C außen ─► #5398 Eing. B ┘
                                   Reed ◄─ Magnet der Box
                     GND ───────────────────────────── Ring-Pins ══► Ring ───────── GND
```

- Der Sockel schaltet Plus erst ein, wenn der Reed den Magneten der Box sieht.
- Die Box nimmt den Strom über die Ideal-Diode #5398. Der PiSugar lädt.
- Masse liegt dauerhaft am Ring. Das ist ungefährlich, weil ohne Plus kein
  Strom fließt.

---

## 3. Kontaktbild und Zentrierung

### 3.1 Kontaktbild (D2, D3)

```
Box-Boden (von unten)          Sockel (von oben)

   ┌─────────────────┐          ┌─────────────────┐
   │ M             M │          │ m             m │
   │     ╭─────╮     │          │        o        │
   │    ╱ Ring  ╲    │          │                 │
   │   │   (●)   │   │          │  o     ●     o  │
   │    ╲ GND   ╱    │          │                 │
   │     ╰─────╯     │          │        o        │
   │ M             M │          │ m             m │
   └─────────────────┘          └─────────────────┘
   ● Mittelfläche = +5 V        ● Mittel-Pin = +5 V
   Ring = GND                   o Ring-Pins = GND
   M = Magnete                  m = Gegenstück, Reed unter einem
```

- **Box:** runde Kontaktscheibe, Mittelfläche Ø 10 mm (R), Spalt 4 mm (R),
  Ring 5 mm breit (R). Außendurchmesser damit ~28 mm.
- **Sockel:** 1 Mittel-Pin (+5 V), 3 Ring-Pins (GND) im 120°-Abstand auf dem
  Ringradius. Drei Pins stehen auch bei leichter Schräglage sicher auf.
- **Plus in der Mitte:** Die Mittelfläche ist klein und tief im Boden, ein
  Finger oder eine flache Münze erreicht sie schwerer als den Ring.
- **Strom:** Mittel-Pin trägt allein den Plus-Strom. Daher einen Pogo-Pin mit
  ≥ 3 A Dauerstrom wählen, oder zwei eng nebeneinander in der Mitte (R).

### 3.2 Zentrierung in zwei Stufen

1. **Grob: Fangtrichter.** Die Mulde im Sockel ist quadratisch wie der Würfel,
   mit 45°-Schrägen nach außen. Ein Kind stellt die Box irgendwo in die Nähe,
   sie rutscht hinein. Spiel am Grund ~1 mm je Seite (R).
2. **Fein: Zentrierzapfen.** Auf dem Sockelboden sitzt ein runder Zapfen, in
   dem die Pins stecken. Die Box hat unten eine passende runde Tasche, 3–4 mm
   tief, an deren Grund die Kontaktscheibe liegt. Der Zapfen zentriert die
   Kontakte auf ±0,5 mm (R).

Die Tasche erfüllt zugleich „Kontakte 3–4 mm versenkt“ (PSP 3.5.3). Eine
flach liegende Münze erreicht die Box-Kontakte nicht. Steht die Box auf dem
Tisch, ruht sie auf dem Rand, nicht auf der Scheibe.

### 3.3 Herstellung der Kontaktscheibe (offen)

| Variante | Vorteil | Nachteil |
|---|---|---|
| Runde Leiterplatte, ENIG-vergoldet, ohne Bauteile | maßhaltig, korrosionsfest, 2 Lötpads hinten | Bestellung mit Wartezeit, ~10–15 € mit Versand für 5 Stück (R) |
| Messing (Scheibe + Ring, eingeklebt) | sofort, im Baumarkt | Ring schwer genau zu fertigen, Messing läuft an |

Vorschlag: Leiterplatte, zusammen mit anderen Teilen bestellen. Entscheidung
Tobias.

---

## 4. Elektrik

### 4.1 Sockel

Je Sockel, alles fertige Module (D7):

| Teil | Aufgabe | Auswahl |
|---|---|---|
| USB-C-Breakout mit 5,1 kΩ an CC1/CC2 | holt 5 V aus dem USB-C-Netzteil | wie in der Box (Stückliste 1.1) |
| PTC (rückstellbare Sicherung) | zweite Schutzschicht nach dem Netzteil | Haltestrom nach Messung PiSugar, Vorschlag 2,5 A Halte-, ~5 A Auslösestrom (R) |
| Pololu #2810 | Load-Switch, schaltet Plus | 3 A Dauerstrom, ON-Pin > 1 V = ein |
| Reed-Kontakt, gekapselt, Schließer | gibt ON frei, wenn Box-Magnet da ist | Typ nach Abstandstest |
| Widerstand 100 kΩ (R) | zieht ON auf GND, wenn Reed offen | nur nötig, falls #2810 keinen eigenen Pulldown hat |
| Pogo-Pins | 1× Mitte, 3× Ring | ≥ 3 A Mitte, ≥ 1 A Ring |

**Schaltung Reed:** Reed zwischen 5 V (nach dem PTC) und ON-Pin des #2810.
Reed zu → ON = 5 V → Schalter ein. Reed offen → ON über Pulldown auf GND →
aus.

**Zu prüfen (Datenblatt #2810, Agent):** Wie spielen Schieber und ON-Pin
zusammen (welche Schieberstellung lässt den ON-Pin steuern)? Hat der ON-Pin
einen eigenen Pulldown? Darf ON dauerhaft auf 5 V liegen?

**Ruhestrom ohne Box:** Load-Switch aus, Reed offen. Es fließt nur der
Ruhestrom von Netzteil und #2810 (Mikroampere bis wenige Milliampere). Keine
LED (A11). Falls der #2810 eine Status-LED hat, wird sie entfernt.

### 4.2 Box

- Kontaktscheibe: Mitte → Eingang A des #5398, Ring → GND.
- USB-C außen → Eingang B des #5398 (unverändert, PSP 3.2.5).
- Ausgang #5398 → Ladeeingang PiSugar 3 Plus.
- Der #5398 sperrt rückwärts: Beim USB-C-Laden liegen an der Kontaktscheibe
  0 V (A5). Prüfung am Muster mit Multimeter (PSP 8.4.5).
- Nichts weiter an der Box. Die Software erkennt „am Lader“ über den PiSugar
  (A12).

### 4.3 Reihenfolge beim Andocken und Abheben

**Andocken:** Der Reed muss erst schließen, wenn die Pins schon auf der Scheibe
aufsitzen. Sonst liegt Plus schon an, bevor die Pins Kontakt haben, und
der erste Kontakt kann funken. Bei 5 V ist das harmlos, aber es nutzt die
Oberflächen ab. Daher Reed-Lage und -Abstand so wählen, dass er erst bei
≤ 2 mm Restabstand schließt (R, Abstandstest).

**Abheben:** Die Pins verlieren den Kontakt, bevor der Reed öffnet. Der
Ladestrom reißt an den Pins ab. Bei 5 V und ~2 A ist das unkritisch (R). Der
PiSugar wechselt auf Akku, die Box läuft weiter.

**Wecken (A7):** Strom am Ladeeingang weckt den PiSugar 3 Plus nur, wenn
Auto-Power-On an ist. Es bleibt aus (PSP 5.6.5). Test PSP 8.2.4.

### 4.4 Strombedarf (A8)

Das Ergebnis der Recherche reicht nicht. Messung am Muster (neu, gehört zu
PSP 3.1):

| Messung | Zustand | Erwartung (R) |
|---|---|---|
| M1 | Akku leer, Box aus, am USB-C-Netzteil | Ladestrom PiSugar, vermutlich 1,5–2,5 A |
| M2 | Akku leer, Box läuft (Sync + Musik laut) | M1 + 0,4–0,6 A |
| M3 | Spannung am PiSugar-Eingang bei M2, über Pogo und #5398 | ≥ 4,75 V (R) |

Ein USB-C-Netzteil mit 3 A je Sockel reicht, wenn M2 ≤ 2,7 A. Der PTC-Wert
folgt aus M2.

---

## 5. Magnete und Reed — *folgt*

## 6. Mechanik Sockel und Box-Boden — *folgt*

## 7. Tests — *folgt*

## 8. Stückliste und Abweichungen vom Plan — *folgt*
