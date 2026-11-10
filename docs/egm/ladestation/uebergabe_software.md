# Übergabe an die Software-Sitzung: Entscheidungen zur Ladestation

Stand 10.11.2026. Kurzfassung der Entscheidungen aus der Ladestation-Sitzung,
für die Sitzung, die die Box-Software gebaut hat. Wie das in Design, Verträge
und Code kommt, entscheidet die Software-Sitzung.

---

In der Ladestation-Sitzung (Branch `claude/ladestation-dock`, Ordner
`docs/egm/ladestation/`) haben Tobias und ich Hardware und Verhalten am Lader
entschieden. Hier ist alles, was die Software betrifft. Die Begründungen
stehen in `docs/egm/ladestation/resolve.md`, die Software-Entscheidungen im
Wortlaut in `docs/egm/ladestation/software_folgen.md`, Abschnitt 10. Den Rest
dieser Datei brauchst du nicht, die Analyse darin stammt von einem Agent ohne
deine Code-Kenntnis.

## Hardware (was sich an der Box ändert)

- **Ladesockel:** Mulde mit einem USB-C-Stecker in der Mitte, wie ein
  Handy-Dock. Der Stecker gehört zum fest angeschlossenen Kabel eines
  Raspberry-Pi-Netzteils (15 W, 5,1 V/3 A). Im Sockel ist keine Elektronik,
  der Sockel sendet kein Signal an die Box.
- **Eine einzige USB-C-Buchse, unten in der Box** (5,1 kΩ an CC). Sie dient
  für den Sockel **und** unterwegs (Powerbank, Auto, beliebiges Netzteil, mit
  gewinkeltem Kabel).
- **Entfallen:** die seitliche USB-C-Buchse, der Pololu #5398 (Ideal-Diode),
  die Pogo-Pins, die Magnete und Reeds. Die Buchse geht direkt an den
  Ladeeingang des PiSugar 3 Plus.
- Die Box steckt nur bei 0° oder 180°. Bei 90° kippelt sie absichtlich auf
  dem Kragen und lädt nicht.

## Verhalten (Entscheidungen von Tobias)

- **R8, Andocken weckt die Box:** Am PiSugar wird „Einschalten bei Strom am
  Eingang“ aktiviert. Das ersetzt Plan-Punkt 3 („Andocken darf nicht wecken“)
  und PSP 5.6.5 und 8.2.4.
- **S1:** Jeder Start mit Strom am Eingang gilt als „Start am Lader“. Es gibt
  keinen Merker. Dass ein Knopfstart am Lader gleich behandelt wird, ist in
  Ordnung.
- **S2:** Nach dem Start am Lader kommt eine Rückmeldung (Ton und LED-Ring mit
  Ladestand), dann die Sync-Prüfung, dann wird die Box nach **120 s** wieder
  ausgeschaltet, statt nach 20 min. Ein laufender Sync hält sie wach.
- **S3:** Ein aufgelegter Tobie, der Hauptknopf (kurz) oder ein HA-Befehl
  beenden diesen Kurz-Modus, danach gilt die normale 20-min-Regel. Weiter,
  Zurück und der Drehregler beenden ihn nicht.
- **S4:** Liegt beim Start schon ein Tobie, spielt er wie bisher (CUJ 20
  unverändert).
- **S5:** In den Leise-Zeiten („leiser“ und „stumm“) kommt beim Andocken kein
  Ton. Der Ring leuchtet gedimmt (etwa 5 % bzw. 3 %), das Lauflicht beim
  Start ist nachts aus.
- **S6: Update vormerken.** In HA lässt sich „Update beim nächsten Andocken“
  vormerken. Die Box holt das Update beim nächsten Start am Lader, wenn die
  bisherigen Bedingungen erfüllt sind (daheim, am Lader, spielt nicht).
- **S7:** Der Start-Sync läuft auch über den Handy-Hotspot. Die bestehende
  Hotspot-Regel („Lader dran“ erlaubt Medien-Sync) bleibt. Weil jetzt jede
  Powerbank als Lader gilt, kann die Box im Auto über den Hotspot laden.
  Tobias nimmt das in Kauf.
- **S8:** Wird die Box angedockt, während sie läuft, prüft sie ebenfalls den
  Sync, einmal je Andocken, 10 s entprellt.
- **S9:** Läuft dabei ein Hörspiel, zeigt nur der Ring den Ladestand, es kommt
  kein Ton.
- **S10:** Es gibt keinen Taster, der Sockel und Kabel unterscheidet. Die
  Software behandelt jede Stromquelle gleich.
- **S11:** Ob der Ring schon früh beim Hochfahren leuchtet, entscheiden wir
  erst nach einer Messung der Startzeit am Muster.

## Noch nicht geklärt (Messungen am Muster)

- Gerät die Box in eine Startschleife, wenn sie herunterfährt, während Strom
  anliegt (Einschalten bei Strom aktiv)?
- Meldet pisugar-server an der einzigen Buchse den Lader weiterhin richtig?
- Wie lange dauert der Start bis zur Rückmeldung?

## Regeln

Es gelten die Regeln aus `CLAUDE.md`: Das EGM-Vorgehen gilt für Änderungen
an Design und Verträgen, Tobias gibt Vertragsänderungen frei.
