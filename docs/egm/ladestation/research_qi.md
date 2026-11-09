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

## Nachtrag: Erfahrungen anderer mit PiSugar + Qi (09.11., Haiku)

PiSugar bietet selbst kein Qi an. Es gibt nur Bastlerberichte, keiner ist ein
sauberer Erfolg:

- **PiSugar/PiSugar #168** (PiSugar 3, Qi-Modul angelötet): Akku und Lader
  wurden **sehr heiß**. Der Pi Zero ging beim Laden **von selbst an**.
  Antwort des Herstellers: Das Modul darf nicht am Akku anliegen. Die
  Modul-Platine hält über 100 °C aus, der Akku verträgt beim Laden nur
  45 °C. Ohne Lösung geschlossen.
  https://github.com/PiSugar/PiSugar/issues/168
- **#62:** Qi lädt nicht, Ursache war vertauschte Verdrahtung. Nach der
  Korrektur lud es. https://github.com/PiSugar/PiSugar/issues/62
- **#73:** Laden über Qi wird ab ~50 % stark langsamer. Keine Lösung.
  https://github.com/PiSugar/PiSugar/issues/73
- **Hackaday (PiSugar Zero):** nur die Idee, kein Test.
- **Phoniebox- und TonUINO-Szene:** keine Kinderbox mit Qi gefunden.

**Folgerung:** Die beiden Hauptrisiken sind real belegt: Wärme am Akku und
Aufwachen beim Laden. Das Aufwachen kann an der Einstellung Auto-Power-On
gelegen haben, das ist nicht geklärt. Qi bleibt nur mit Wärmetest machbar,
der Vorsprung gegenüber den Kontakten wird kleiner.
