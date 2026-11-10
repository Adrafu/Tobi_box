# Tobi Box

Zwei baugleiche, mobile Hörspielboxen für Kleinkinder, als privates Bastelprojekt. Eine Figur oder
NFC-Karte auf die Box legen, und das passende Hörspiel spielt. Dazu kommen ein Ladesockel und eine
Anbindung an Home Assistant.

- **Hardware:** Raspberry Pi 3 Model A+, PiSugar 3 Plus, NFC-Leser PN5180 an einem ESP32-S3, I²S-Verstärker, LED-Ring
- **Software:** eigener Box-Dienst auf MPD (`box/`), Leser-Firmware (`firmware/`), Home-Assistant-Integration (`homeassistant/`)
- **Plan und Entscheidungen:** `docs/plan/` · **Design:** `docs/designs/` · **Verträge:** `docs/protocol/`, `docs/data-model.md`

Die Dokumente sind auf Deutsch. Im Projekt heißen Figuren und NFC-Karten zusammen **Tobies**.

## Marken und Abgrenzung

„tonies“, „Tonie“ und „Toniebox“ sind Marken der tonies GmbH. Dieses Projekt ist ein unabhängiges,
nicht-kommerzielles Hobbyprojekt. Es ist **nicht** mit der tonies GmbH verbunden und wird von ihr weder
unterstützt noch geprüft. Die Marken werden nur beschreibend genannt, damit klar ist, welche Figuren die Box
erkennt.

Das Repo enthält **keine** Inhalte, Logos, Bilder, Hörspiele oder Firmware der tonies GmbH und keine
Passwörter oder Schlüssel. Die Box spielt nur eigene Audiodateien von der eigenen Festplatte. Alle Töne und
Sprachansagen im Repo sind selbst erzeugt (freie Stimme „Thorsten“, CC0).

## Lizenz

MIT, siehe `LICENSE`. Abhängigkeiten wie die PN5180-Bibliothek werden beim Bauen geladen und behalten ihre
eigenen Lizenzen.
