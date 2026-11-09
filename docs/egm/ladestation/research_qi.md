# Recherche: Induktiv laden (Qi) für die Box

* **Datum:** 2026-11-09 · **Quelle:** Haiku-Agent, Suchauszüge (kaum volle Datenblätter)
* **Anlass:** Sanity Check im Resolve (`resolve.md`)

## Ergebnis

- **Leistung:** Qi-Basis (BPP) überträgt bis 5 W. Ein Empfänger mit 5 V und
  1 A reicht für die Box (1,1–1,9 W) plus Laden. Ein Modul mit 5 V und
  ≥ 1,5 A wurde nicht gefunden, dafür wäre eine eigene Platine nötig.
- **Empfänger-Kandidaten:**
  - Seeed 106990017: Kit aus Sender und Empfänger, 5 V/1 A, flache
    Spule auf Folie (1,2 mm). Ob es Qi-konform ist, ist offen.
  - Adafruit 1901 (TI BQ51013B): Qi, gut dokumentiert, aber nur
    **500 mA**. Das ist zu knapp, wenn die Box läuft und lädt. ~15–30 €.
  - Billigmodule 5 V/1 A (AliExpress, Daokai): Angaben ungeprüft.
  - DFRobot DFR0362 ist kein Qi und fällt raus.
- **Fremdmetall:** Die Qi-Norm schreibt die Erkennung von Fremdmetall (FOD)
  vor, Münze und Alufolie sind Prüfkörper der Norm. Kleine oder dünne Teile
  können aber unter der Schwelle bleiben. Belastbare Praxistests einzelner
  Pads wurden nicht gefunden.
- **Versatz:** Bei etwa 10 mm Versatz bricht das Laden ab. Die Drehung ist
  egal. Die Mulde muss also auf wenige Millimeter zentrieren. Das schafft ein
  einfacher Trichter ohne Zapfen.
- **Wärme:** Es gibt keine Messdaten für 5 W neben einem Akku. Üblich sind
  eine Ferritplatte zwischen Spule und Akku und ≥ 5 mm Abstand. Am Muster
  messen.
- **NFC:** Qi (~100–200 kHz) und NFC (13,56 MHz) stören sich kaum, bei 10 cm
  Abstand unkritisch.
- **Hauptrisiko „Pumpen“:** Der Empfänger begrenzt beim Anlauf auf
  ~0,3–0,4 A (BQ51013). Zieht der Ladechip des PiSugar mehr, als der
  Empfänger liefert, bricht die Spannung ein. Der Sender kann dann abschalten
  und wieder starten. In Foren gibt es Berichte über solche Abbrüche. Ob der
  PiSugar seinen Eingangsstrom bei sinkender Spannung zurücknimmt, ist
  unbekannt. **Nur ein Test klärt das.**

## Einordnung

Qi löst alle Probleme der offenen Kontakte: keine Kontakte, keine Magnete,
keine Reeds, keine eigene Sockel-Platine. Das Risiko wandert in die Box:
Kommen Empfänger und PiSugar-Ladechip miteinander aus, und wie warm wird es
am Akku? Beides ist billig zu testen.
