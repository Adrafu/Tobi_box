# Ladestation (Dock) Tobi Box

* **Autor:** Tobias (Projektleitung: Claude als „Elefant“)
* **Datum:** 2026-11-09
* **Stand:** Brainstorm abgeschlossen, Grundlage für den Draft
* **Grundlage:** `docs/plan/stueckliste-und-psp.md` (Punkte 3, 7, 10, 11, 13,
  15, Abschnitt „Load-Switch im Dock, Ideal-Diode in der Box“, Stückliste
  1.1/1.2, PSP 3.5, 3.6, 4.4, 8.2.4, 8.3.4, 8.4.5),
  `docs/designs/box-software.md` (CUJ 10, CUJ 16, Strom / Leerlauf)

## Problem

Zwei baugleiche Boxen sollen daheim laden, ohne dass jemand ein Kabel
einstecken muss. Die Zwillinge stellen ihre Box selbst ab, auch im Dunkeln.
Andocken darf die Box nicht wecken. Weder am Dock noch an der Box dürfen offene
Kontakte Spannung führen, wenn keine Box aufsitzt. Eine Münze oder ein Löffel
darf nichts anrichten.

## Was schon feststeht (aus dem Plan)

- Je Ladeplatz ein Load-Switch. Er schaltet nur ein, wenn ein Reed-Kontakt im
  Dock geschlossen ist. Ausgelöst wird der Reed-Kontakt vom Zentriermagnet der
  Box. Es gibt keinen dritten Pin (Punkt 11).
- In der Box trennt der Pololu Power-ORing #5398 Pogo-Eingang und USB-C
  (Punkt 7). Beim USB-C-Laden liegt an den Box-Kontakten keine Spannung.
- 2-polige gefederte Kontakte, 3–4 mm versenkt (PSP 3.5.3).
- Vier Neodym-Magnete 8×3 mm in der Box zur Zentrierung, voll eingeschlossen
  und eingeklebt (Punkt 13, PSP 4.7.1).
- Kein eigener Laderegler, das Laden macht der PiSugar 3 Plus.
- Auto-Power-On am PiSugar aus, Andocken weckt nicht (PSP 5.6.5, 8.2.4).
- Software: Die Box erkennt „am Lader“ selbst über den PiSugar. Sie braucht
  kein Signal vom Dock. Am Lader: Sync, Update (nur dort), Abschalten erst,
  wenn beide fertig sind (CUJ 10, CUJ 16). Der LED-Ring zeigt am Lader den
  Akku in Blau.
- Gehäuse: Würfel ca. 12 cm (Annahme, noch kein CAD), PETG, schwarze
  TPU-Ecken. Box 1 Mivolve PETG Blue, Box 2 Königsblau.

## Entscheidungen aus dem Brainstorm (09.11.)

| # | Frage | Entscheidung |
|---|---|---|
| D1 | Wer dockt an? | Die Kinder selbst, **auch blind**. Großer Fangtrichter, die Magnete ziehen die Box in Lage. Die Haltekraft muss klein genug sein, dass ein Kleinkind die Box einhändig abhebt. |
| D2 | Drehlage | Die Box passt in **jeder der vier Drehlagen**. Das Kontaktbild ist drehsymmetrisch (Mittelkontakt + Ring). Damit ist Verpolung durch die Form ausgeschlossen. |
| D3 | Wo sitzen die Federn? | **Gefederte Pogo-Pins im Dock**, flache, versenkte Kontaktflächen unten an der Box. |
| D4 | Form und Standort | **Zwei Einzelsockel**, je einer pro Box. Sie können getrennt stehen (z. B. je am Bett). |
| D5 | Netzteil | **Je Sockel ein eigenes USB-C-Netzteil** (5 V, bis 3 A). Kein Verbindungskabel zwischen den Sockeln. |
| D6 | Anzeige | **Keine LED am Sockel.** Den Ladezustand zeigt die Box. |
| D7 | Bauweise | **Fertige Module** (USB-C-Breakout mit 5,1 kΩ an CC, Pololu-Schalter #2810, rückstellbare Sicherung PTC, Reed). Der Wechsel auf eine eigene eFuse-Platine bleibt offen, wenn Messung oder Münztest das verlangen. |

### Nachtrag zu D2: So funktioniert „jede Drehlage“ (09.11.)

Die Pins müssen nicht an festen Stellen der Box landen, nur im richtigen
**Abstand zur Mitte** (Prinzip Wasserkocher-Sockel). Die Box dreht sich immer
um ihre Mitte. Der Mittel-Pin trifft daher immer die Mittelfläche, die
Ring-Pins treffen in jedem Winkel den Ring.

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
   Ring = GND                   o Ring-Pins (2–4) = GND
   M = Magnete                  m = Gegenstück, Reed unter einem
```

- Plus immer in der Mitte, Masse immer außen: Verpolung geht nicht.
- Die vier Eck-Magnete liegen im 90°-Raster, in jeder Lage sitzt einer über
  dem Reed.
- Richtwerte: Mittelfläche Ø 8–10 mm, Ring 4–5 mm breit, Spalt Mitte–Ring
  ~4 mm.
- Die Flächen entstehen als runde Leiterplatte ohne Bauteile (vergoldet) oder
  aus Messing. Offen für den Draft.
- **Budget (Tobias, 09.11.: rausnehmen, wenn es das Budget stark belastet):**
  Mehrkosten gegenüber 2 Pins etwa 10–20 € gesamt (Pad-Platinen inkl. Versand,
  2–3 zusätzliche Pogo-Pins je Sockel). Das belastet das Budget nicht stark,
  D2 bleibt.

### Folgen und Abweichungen vom Plan

- **Stückliste 1.2 ändert sich:** statt einer „Dual-Ladestation mit 5 V/4 A“
  zwei Einzelsockel mit je einem USB-C-Netzteil. Ein Netzteil für zwei Plätze
  und die Lastverteilung fallen weg. Je Platz stehen bis zu 3 A zur Verfügung.
  Kosten neu zu schätzen (2 Netzteile, falls keine vorhandenen genutzt werden).
- **Zwei Schutzschichten gegen Kurzschluss:** Ein Markennetzteil schaltet bei
  Kurzschluss selbst ab, dazu kommt der PTC im Sockel. Eine echte, schnelle
  Strombegrenzung (eFuse) gibt es erst mit eigener Platine.
- **Kein Signal Dock → Box nötig:** Die Software erkennt „am Lader“ über den
  PiSugar (Strom am Eingang). Verträge in `docs/protocol/` bleiben unberührt.

## Recherche (Haiku-Agent, 09.11.)

Quellen siehe Agent-Bericht; hier nur das Ergebnis.

- **PiSugar 3 Plus:** Wie viel Strom er beim Laden höchstens aufnimmt und
  welcher Ladechip verbaut ist, war **nicht belegbar**. Laut Wiki unterstützt
  er Betrieb während des Ladens. → Am Muster messen.
- **Pololu #5398:** 4–60 V, 6 A je Kanal, < 10 mΩ, zusätzlich 20 mΩ
  Ausgleichswiderstand (per Jumper überbrückbar). Abfall bei 2,5 A etwa
  25–75 mV, unkritisch.
- **Pololu #2810 (Load-Switch):** 2–20 V, ~3 A Dauerstrom, schaltet bei einem
  Logiksignal > 1 V am ON-Pin, also direkt über den Reed. **Keine
  Strombegrenzung.** Ein fertiges Modul mit ≥ 2,5 A und eingebauter
  Strombegrenzung wurde nicht gefunden.
- **Reed-Kontakt:** Bei welchem Abstand er mit 8×3-mm-Magnet schaltet, ist
  nicht gefunden → Test. Glas-Reeds brechen, gekapselte Bauform bevorzugen.
  Alternative Hall-Schalter (z. B. DRV5032-Modul): keine bewegten Teile, aber
  ständiger Ruhestrom.
- **Pogo-Pins:** Übliche Typen tragen 2 A dauerhaft, 3 A kurz, Federweg
  0,6–1,4 mm. Bei 2–3 A je Pol mehrere Pins parallel.
- **USB-C:** Ohne Power Delivery höchstens 5 V / 3 A. Der Sockel braucht nur
  5 V, also reicht ein USB-C-Breakout mit 5,1 kΩ an CC.

## Grenzen

- Keine Firmware oder Software im Dock. Das Dock ist rein passiv bis auf den
  Schalter.
- Kein Laderegler im Dock, kein Datenkontakt.
- Andocken weckt die Box nicht.
- Nichts Abziehbares, Magnete und Kleinteile unzugänglich (Punkte 13–15).
- Das NFC-Kartenfeld liegt oben, die Kontakte unten. Bei ~12 cm Würfel sind
  das ~10 cm Abstand, Punkt 10 (Metall ≥ 2–3 cm weg) ist damit erfüllt. Zu
  prüfen bleibt nur ein Magnet in der Mitte des Bodens, falls einer dorthin
  kommt.

## Offene Fragen für den Draft

1. **Magnet-Anordnung bei vier Drehlagen:** Vier Magnete in den Ecken des
   Bodens sind drehsymmetrisch. Was zieht im Sockel dagegen: Stahlscheiben oder
   Gegenmagnete? Gegenmagnete müssen in allen vier Lagen anziehen, also gleiche
   Polung überall. Haltekraft so wählen, dass ein Kleinkind abheben kann.
2. **Reed-Lage:** Der Reed muss in jeder Drehlage unter einem Box-Magnet sitzen,
   darf aber nicht von einer Stahlscheibe abgeschirmt werden. Schaltabstand und
   Hysterese am Muster messen.
3. **Kontaktbild:** Mittelkontakt + Ring. Welcher Pol in die Mitte? Wie viele
   Pogo-Pins auf dem Ring, damit 2–3 A sicher fließen? Breite des Rings bei
   Fangtrichter-Spiel.
4. **Münze und Löffel:** Eine Münze kann Mitte und Ring der Box gleichzeitig
   berühren. Die Box-Seite ist durch den #5398 spannungslos. Die Dock-Seite ist
   ohne Box durch den Reed spannungslos. Was passiert, wenn ein Magnet (z. B.
   Kühlschrankmagnet, Tonie-Sockel) den Reed auslöst und gleichzeitig ein
   Löffel auf den Pins liegt? → Netzteil und PTC müssen das abfangen, Test
   3.5.4.
5. **Ladestrom:** Was nimmt der PiSugar 3 Plus auf, wenn der Akku leer ist und
   die Box läuft (Sync, Musik)? Reichen 3 A je Sockel sicher? Abfall über Kabel,
   Pogo und #5398 bei diesem Strom.
6. **Sockelform:** Fangtrichter-Maße zum Würfel 12 cm, Standfestigkeit (die
   Box wird abgehoben, der Sockel darf nicht mitkommen), Gewicht oder
   rutschfeste Füße, Kabelführung und USB-C-Buchse an der Rückseite.
7. **Bauhöhe:** Passen Breakout, #2810, PTC, Reed und Pogo-Halter unter die
   Mulde?
8. **Bezug in Österreich:** Pololu-Händler, Reed gekapselt, Pogo-Pins,
   Netzteile.

## Nächster Schritt

Draft `docs/egm/ladestation/design_draft.md` abschnittsweise:
Anforderungen → Elektrik je Sockel → Kontaktbild → Magnete und Reed →
Mechanik Sockel und Box-Boden → Tests (Münze, Löffel, Andocken, Ladestrom) →
Stückliste.
