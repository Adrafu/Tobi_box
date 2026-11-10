# Einkaufsliste Muster Ladesockel (Rev. 3)

Stand: Abrufdatum 10.11.2026. Nur Recherche, **nichts bestellt**. Grundlage ist
`design_draft.md` Rev. 3 (Abschnitte 3, 6 T0/T1, 7). Preise sind Suchtreffen aus
Händler- und Datenblatt-Seiten, nicht live geprüft. Lieferzeiten nach AT sind
nur angegeben, wenn eine Seite sie nennt.

Kennzeichnung im Text:
- **[gelesen]**: steht so auf einer Seite, die ich gesehen habe
- **[Schätzung]**: eigene Annahme oder Umrechnung
- **[offen]**: nicht gefunden oder widersprüchlich

---

## 1. Magnet-Pogo-Stecker (Schwerpunkt 1)

Anforderung aus dem Entwurf: 4-polig, je Pin ≥ 1,5 A Dauerstrom, vergoldet,
≥ 10.000 Zyklen, Magnete im Gehäuse, Federweg ≥ 1 mm, Fangbereich ≥ 1,5 mm.

**Korrektur zum Entwurf:** Die Angabe „Multicomp Pro MP011967/68 (Farnell, 2 A)“
in Abschnitt 3.2 ist falsch. MP011967 ist ein **2-poliger** Stecker [gelesen,
Farnell/element14-Seite]. Der 4-polige Multicomp-Typ ist **MP011976**.

| Typ | Daten | Preis | Link | Bewertung |
|---|---|---|---|---|
| **A. Multicomp Pro MP011976** (Markenstecker, Farnell/element14), Plug, gerade, 4 Kontakte | Pitch 2,54 mm; **2 A** Nennstrom (Angabe ohne Pin-Aufteilung); Spannung nicht angegeben; Zyklen, Vergoldung, Magnet im Gehäuse: **[offen]**, Datenblatt-PDF auf Farnell, nicht gelesen | Farnell JP: ¥2.245 netto (¥2.469 inkl. Steuer) [gelesen]; EU-Preis nicht gefunden [offen]. Schätzung ca. 12–15 € je Paar [Schätzung] | Farnell-Bestellnr. 4178988, z. B. https://uk.farnell.com/multicomp-pro/mp011976/magnetic-conn-plug-4pos-2a/dp/4178988 | Gut: Markenteil, Datenblatt verlinkt. Schwach: 2 A ist knapp über dem Ziel 1,5 A je Pin, ob das je Pin gilt, ist offen. 2 Pins parallel je Plus/Masse würden den Strom verdoppeln, das ist aber nicht belegt. Lieferzeit AT: **[offen]** |
| **B. Mill-Max Maxnetic 878**, 4-polig (Digi-Key-Nummer 878-22-004-10-011101 laut Suche, Teilnummer-Logik [Schätzung]) | Herstellerangabe: **7,2 A je Pin** in freier Luft, de-rated [gelesen, Pressetext]. Datenblatt eines 2-poligen Typs 878-22-002-10-011101 nennt **9 A je Pin bei 30 °C Temperaturanstieg** [gelesen, Suche]; im Stecker niedriger, sagt Mill-Max selbst. Magnet-Einschluss: **[offen]**. Zyklen: **[offen]** | Preis: **[offen]**. Keine Händler-Seite mit Preis gefunden | https://www.mill-max.com/products/datasheet/sockets/878-22-002-10-011101 (2-polig, als Referenz); 4-polige Datenblätter bei Digi-Key/Farnell (PDFs wurden nicht lesbar abgerufen) | Stärkster Strom-Spielraum, Marke mit Datenblatt. Der PDF-Abruf kam nicht als Text an, die Werte stammen aus Suchausschnitten. Bei 4-poligen Typen vor dem Kauf Datenblatt selbst prüfen |
| **C. Promax NF-Serie 4-polig** (z. B. NF6215-04PA, mit Magnet; NC = ohne Magnet) (AliExpress-Stil, Hersteller-Shop) | Hersteller-Seite: 4-polige Typen mit Präfix NF = Magnet drin, NC = ohne [gelesen]. Seite nennt allgemein **4 A je Kontakt bei 12 V**, **10.000 Zyklen**, Vergoldung über Kupferlegierung [gelesen, Seite allgemein, nicht je Typ]. Pitch, Maße je Typ: **[offen]**. **NF6266 als 4-polig nicht gefunden**; die einzige NF6266-Seite ist 2-polig [gelesen] | Preis: **[offen]**. Hersteller-Shop: https://promaxpogopin.com/magnetic-connector-4pin/ (Liste mit 32 Typen) | Kandidat, weil NF = Magnet drin und Herstellerangaben da sind. Vor Auswahl je Typ Datenblatt holen. Ein Anfrage-Mail an Promax wäre der schnellste Weg zu NF-Datenblatt und Preis |
| **D. (Ersatz, falls A–C nicht passen)** ATTEND 303-Serie (Digi-Key) | Serie: vergoldet über Nickel, 1–3 A je Serie [gelesen]. 4-polige Teile der Serie sind **303C**, nicht 303D (303C-C4115-30-04, 3,00 mm Pitch) [gelesen]. Magnet-Einschluss und Stromangabe je Teil: **[offen]** | Preis: **[offen]**. Digi-Key-Seite für 303 Serie: https://www.digikey.at/en/product-highlight/a/attend/303-series-pogo-pin-connectors | Nur Reserve. Die 303-Serie ist nicht als Magnet-Stecker belegt, Magnet-Ausführung nicht geprüft |

**Empfehlung für T0 (zwei Typen kaufen):** Typ A (Markenstecker, Datenblatt)
und Typ C (Promax NF, Magnet im Gehäuse, Herstellerangaben). Typ B nur, wenn
Datenblatt zeigt, dass er als 4-Pin-Magnetstecker mit geschlossenem Magnet
erhältlich ist. Vor dem Kauf offen: Pin-Strom je Kontakt bei 4-poligen Typen,
Magnet-Einschluss, Lieferzeit AT.

**Hinweis zur Stückzahl:** Entwurf nennt 5 Paare. Für 2 Einbau-Sets (je ein
Paar) plus T0 mit 2 Typen × 1–2 Paare sind 4–6 Paare sinnvoll.

---

## 2. Übrige Teile (Schwerpunkt 2)

| Teil | Menge | Artikel | Händler | Preis | Link |
|---|---|---|---|---|---|
| Pololu #2810 (Load-Switch, Schieber) | 2 (+1 Reserve) | Mini MOSFET Slide Switch with Reverse Voltage Protection, LV | **Botland** [gelesen]: 4,50 € brutto (3,66 € netto), Versand 24 h. **Exp-tech.de**: 3,72 € netto + Versand [gelesen]. Eckstein führt #2810 laut Pololu-Händlerliste [gelesen], Preis nicht gefunden [offen] | Botland: https://botland.store/digital-switches/4852-mini-switch-slide-mosfet-lv-2-20v6a-with-protection-before-reverse-current-pololu-2810-5904422300043.html; Pololu: https://www.pololu.com/product/2810 | **Widerspruch:** Pololu nennt bis ca. 6 A Dauerstrom, eine Drittseite nennt 4 A mit Kühlung. Für 2–3 A ist beides ausreichend. Pololu-Empfehlung bis 16 V, Versorgung 5 V ist unkritisch [gelesen] |
| USB-C-Breakout, 5,1 kΩ je CC auf GND (Sink, nur 5 V) | 2 (+1 Reserve) | z. B. Pololu USB 2.0 Type-C Breakout (hat 5,1 kΩ an CC1/CC2 [gelesen]); Adafruit-Downstream-Board (Sink-Auslegung [gelesen]) | Pololu-Shop oder EU-Händler: **Preis [offen]**. Schätzung 4–8 € je Stück [Schätzung] | Pololu-Produkt "USB 2.0 Type-C Connector Breakout Board" über https://www.pololu.com/blog/790 (Hinweis) | Prüfen: Breakout muss **nur 5 V** liefern und keine Datenleitungen verschalten. Die gesuchte 16-polige Variante ist nicht belegt [offen] |
| PTC bedrahtet, Haltestrom 2,5 A | 2 | **Littelfuse RXEF250** (Polymer-PTC, radial) | Farnell (Haltestrom 2,5 A, Auslösestrom 5 A, 72 V [gelesen]); Digi-Key, LCSC: Preis **[offen]** | https://www.digikey.com.mx/en/products/detail/littelfuse-inc/RXEF250/5015991 (Referenz) | **Achtung:** T0 testet mit 2,7 A über 1 h. Bei 2,5 A Haltestrom kann der PTC dabei auslösen. Der Entwurf verlangt Haltestrom ≥ 1,3 × Ladestrom, das ist damit nicht sauber geprüft. Alternative 3,0 A (RXEF300 o. ä., Teilnummer [offen]) gleich mitbestellen |
| PTC Alternative | 1 je Sockel | 2,0 A und 3,0 A Typ (Littelfuse-Familie RXEF) | [offen] | [offen] | [offen] |
| TVS bedrahtet | 2 | **P6KE6.8A** (= "P6KE6V8A" im Entwurf, gleicher Typ) | DigiKey (Bestand laut Suche sehr hoch, [gelesen]); RS Components: Preis netto 1 Stk [offen] | https://azcus.digikey.com/en/products/detail/littelfuse-inc/P6KE6-8A/285914 | Standoff 5,8 V, Klemmspannung 10,5 V [gelesen]. Reichelt/Botland-Listung nicht gefunden [offen] |
| Elko 100 µF / 10 V, radial | 2 | Würth 860130273002 (100 µF 10 V radial) [gelesen] | Würth-Preis ab 1500 Stk 0,22 €; Kleinmenge **[offen]**. Rubycon 10PX100MEFC5X11 bei Digi-Key, Lieferzeit 21 Wochen [gelesen] | https://www.radiomag.com.de/product/860130273002.html | Kleinmenge-Händler (Reichelt, Conrad AT, Bürklin) **[offen]**. Vishay MAL2021… ist axial, nicht passend |
| Elko oder Kerko 10 µF | 2 | — | — | Schätzung 0,50 € [Schätzung] | — |
| Widerstände 100 kΩ (3 je Sockel) | 6 | E-Reihe, Kohle oder Metallfilm | — | Schätzung 3–5 € Satz [Schätzung] | — |
| Reed-Kontakt, gekapselt, Typ 1: **Littelfuse 59135** | 4 Einbau + 1 Test | 59135-010 (1 Form A, 10 W, 200 V, 0,5 A) [gelesen, Bürklin]; 59135-030 [gelesen] | Bürklin 59135-010: 6,75 € bzw. 7,58 € Einzelpreis (zwei Listen) [gelesen]; RS Components 59135-030: 7,19 € netto, 8,56 € inkl. MwSt. [gelesen] | https://www.buerklin.com/en/electromechanics/sensors/proximity-switches-reed-switches/c/30141200 (Kategorie) | **Empfindlichkeit AT:** Buchstabe S/T/U/V in der Bestellnummer, konkrete AT-Werte je Buchstabe **[offen]**, Datenblatt-Tabelle in Suchausschnitten unlesbar. Vor Bestellung Datenblatt prüfen |
| Reed-Kontakt, gekapselt, Typ 2: **Standex MK04-1A66B-500W** | 2 (Ersatz für T1) | MK04-1A66B-500W, Schließer [gelesen] | Bürklin: 5,62 € Einzelpreis, 4,17 € ab 250 Stk [gelesen] | https://www.buerklin.com/en/p/30G243/ | Empfindlichkeit: Händlerangaben widersprüchlich (10–15 AT laut einer Listung, 15–20 AT bei anderem Typ [gelesen]). Datenblatt prüfen. MK04 hat Kunststoffgehäuse mit Vergussmasse, Glasröhrchen innen [gelesen] |
| Netzteil Raspberry Pi 15 W USB-C, EU-Stecker | 2 (+1 optional) | Offizielles Raspberry Pi 15W USB-C PSU, EU; 5,1 V / 3 A [gelesen] | **Kein AT-Händler gefunden** (Suche). Elektor DE: 9,95 € inkl. MwSt. (älterer Listungsname) [gelesen]; aio.lv (LV): 15,49 € inkl. Steuer [gelesen]; The Pi Hut (UK): £7,70 inkl. MwSt. [gelesen]; buyzero.de: 8,72 € (ausverkauft) [gelesen] | https://thepihut.com/collections/raspberry-pi-power-supplies/products/raspberry-pi-psu-eu (UK, nur Referenz); Botland und Pi-Shop nicht gefunden | Kein Botland-Preis gefunden. Ein AT-Händler (Reichelt, Conrad AT, Pi-Shop, Botland) muss direkt geprüft werden. Vorsicht: Das Netzteil ist für Pi 4/400 gedacht [gelesen] |
| Lochrasterplatine, Litze, Schrumpf | je 1 Satz | — | Schätzung 5 € [Schätzung] | — | — |

---

## 3. Summe (Schätzung)

Die Summe ist grob. Magnet-Stecker sind der größte Unsicherheitsfaktor, weil
EU-Preise und Pin-Strom fehlen.

| Posten | Stück | Schätzung € |
|---|---|---|
| Netzteil 15 W | 2 | 18–30 |
| Magnet-Stecker 4-polig (4–6 Paare, je ca. 12–15 €) | 4–6 | 50–90 |
| Pololu #2810 (Botland 4,50 € brutto) | 2–3 | 9–14 |
| USB-C-Breakout | 2–3 | 8–20 |
| Reed 59135 (ca. 7 €) und MK04 (ca. 5,60 €) | 6 | 35–45 |
| PTC, TVS, Elko, Kerko, Widerstände, Platine, Litze | Satz | 15–25 |
| **Summe (Schätzung)** | | **ca. 135–225 €** |

**Vergleich:** Der Entwurf rechnet mit ca. 73 € (Abschnitt 7). Die Reeds
allein kosten nach den gefundenen Preisen rund 35–45 € statt der dort
angesetzten 15 €. Der Entwurf sollte nachgerechnet werden.

---

## 4. Offene Punkte

1. Pin-Strom je Kontakt, Magnet-Einschluss, Zyklen und EU-Preis für die
   4-poligen Stecker sind **nicht belegt**. Datenblätter (MP011976, Promax NF,
   Mill-Max 878 4-polig) vor der Auswahl lesen, oder bei Promax direkt anfragen.
2. Multicomp MP011976: 2 A je Stecker, nicht je Pin. Gilt die Angabe je Pin oder
   je Stecker?
3. PTC 2,5 A gegen den T0-Test mit 2,7 A: Entscheidung über 3,0 A oder
   Testwert anpassen.
4. Reed-AT-Werte je Buchstabe (59135 S/T/U/V) und MK04-Untertyp aus Datenblatt
   klären.
5. AT-Händler für Netzteil (Pi-Shop, Reichelt, Conrad AT, Botland) prüfen.
6. Eckstein-Preis für Pololu #2810 prüfen (nur Händlerliste gefunden).
7. USB-C-Breakout mit 5,1 kΩ: konkreter Artikel und Preis fehlen.
8. Lieferzeiten nach AT: nur für Rubycon (21 Wochen, nicht unsere Wahl)
   belegt, sonst offen.
9. Der Entwurf nennt "Stückliste 73 €" und 15 € für Reeds. Mit den gefundenen
   Preisen ist das zu niedrig.
