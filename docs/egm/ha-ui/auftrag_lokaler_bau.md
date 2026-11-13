# Auftrag für die lokale Bau-Sitzung auf Tobias’ Mac: neue HA-Seite fertig bauen, einspielen, im echten HA prüfen

Diesen Text (ab der Linie) als erste Nachricht in eine **lokale** Claude-Code-Sitzung kopieren (Claude-Desktop-App oder
`claude` im Terminal), Arbeitsordner `~/Tobi_box`. Ab jetzt baut diese Sitzung die Seite weiter; die Cloud-Sitzung
baut an der Seite nichts mehr, sobald der laufende Stand von A9/A10 gepusht ist (siehe „Übergabe“).

---

Du übernimmst den Bau der neuen Home-Assistant-Seite „Tobi Box“. Der Entwurf ist fertig und abgestimmt; es geht nur
noch ums Umsetzen, Einspielen und Prüfen im echten HA.

## 1. Lesen, bevor du etwas tust

1. `CLAUDE.md` (Regeln: Rollen, EGM, keine echten Namen im Repo, Deutsch, Abnahmen mit Tobias Schritt für Schritt).
2. Design: `docs/designs/ha-oberflaeche.md`, besonders Abschnitt 15 (Arbeitspakete und Abnahmen).
3. Entscheidungen: `docs/egm/ha-ui/resolve.md` (alle Runden; was dort steht, gilt vor dem Design).
4. Vertrag: `docs/protocol/ha-websocket-v1.md`, `docs/data-model.md`. **Verträge änderst du nie eigenmächtig**;
   brauchst du eine Änderung, schreibst du sie als Vorschlag auf und fragst Tobias.
5. Stand und Befunde: `docs/plan/stueckliste-und-psp.md` (Rev. 3.22 und Nachträge), `docs/egm/ha-ui/abnahme_a1a_lokal.md`.
6. Code: `homeassistant/custom_components/tobibox/` (Backend Python, Seite unter `frontend/`: `tobibox-app.js`,
   `bausteine.js`, `texte.js`, `seiten/*.js`), Tests unter `homeassistant/tests/` (pytest) und
   `homeassistant/tests/frontend/` (`node --test` mit jsdom, Browser-Prüfung `browser/pruefe_seite.py`).

## 2. Stand und Reihenfolge

- Fertig und abgenommen: A0 (Verträge), A1–A4, A9c (Backend), **A-1a** (Start, Bibliothek, Suche, Serienseite, Geräte,
  Abends, Technik).
- Gerade aus der Cloud gekommen: **A9/A10** (Tobies-Regal, Neuer Tobie, Warteschlange, „Gespielt von“). Prüfe nach
  `git pull`, ob es im Branch ist (Commit-Nachricht mit „A9“/„A10“). Wenn ja: im echten HA prüfen und nachbessern.
- Danach in dieser Reihenfolge (Design Abschnitt 15): A14-1b, A15-1b → **Abnahme A-1b mit Tobias** → A8f, A11a, A11b,
  A14-1c, A15-1c → **Abnahme A-1c** → A17 (Seite für alle öffnen, nur nach Tobias’ Ja) → A6m/A8m (Bewegung) →
  A-2 (Reinhören) → A-3.
- Vor jeder Abnahme: alles grün (pytest, jsdom, Browser-Prüfung) **und** im echten HA selbst durchgeklickt.

## 3. Arbeitsweise

- Du bist Koordinator: Code schreiben Unter-Agents, immer mit dem billigsten passenden Modell (siehe `CLAUDE.md`).
  Kleine Korrekturen nach dem Prüfen im echten HA darfst du direkt machen, wenn ein Agent dafür übertrieben wäre.
- Je Paket: bauen lassen → Tests → einspielen → im echten HA am Desktop **und** in Handy-Breite durchklicken
  (Screenshots ansehen) → nachbessern, bis es sauber ist → committen und pushen.
- Prüfe im echten HA immer über **echte Klicks** (HA fängt Link-Klicks ab, siehe B1 in `abnahme_a1a_lokal.md`).
- Was du im echten HA findest und das Prüfskript nicht gesehen hat: Prüfskript so erweitern, dass es das künftig findet.
- Entscheidungen, die das Design nicht beantwortet oder ändern würden: **Tobias fragen**, dann in `resolve.md`
  festhalten. Kleine technische Festlegungen darfst du selbst treffen; schreib sie in `docs/plan/stueckliste-und-psp.md`.
- Abnahmen gehen mit Tobias **gemeinsam im Chat Schritt für Schritt**: ein Schritt, was er sehen soll, auf seine
  Antwort warten.

## 4. Einspielen in Tobias’ HA

- HA läuft auf dem QNAP, Version 2026.11.x. Die Konfiguration ist per Samba erreichbar, z. B. `smb://<HA-Adresse>/config`
  (im Finder verbinden lassen; Tobias kennt die Adresse und meldet sich selbst an). Prüfe, unter welchem Pfad die
  Freigabe auf dem Mac eingehängt ist (meist `/Volumes/config`).
- Einspielen = Ordner `custom_components/tobibox` auf der Freigabe **ersetzen** (vorher den alten als Zip **außerhalb**
  von `custom_components` sichern, z. B. `/Volumes/config/tobibox_sicherung/<datum>.zip`; nie einen zweiten Ordner mit
  `manifest.json` in `custom_components` liegen lassen, sonst lädt HA die falsche Fassung).
- Nur Dateien der Seite (`frontend/`) geändert: kein Neustart nötig, die Seite im Browser neu laden (die Dateien kommen
  mit `Cache-Control: no-cache`).
- Python geändert: HA neu starten. Dafür einen **langlebigen Zugriffstoken** von Tobias nutzen (er legt ihn in seinem
  HA-Profil an und speichert ihn selbst lokal, z. B. im macOS-Schlüsselbund oder in `~/.config/tobibox/ha_token`, Rechte
  600). Der Token kommt **nie** ins Repo, in Logs oder in Commits. Neustart per
  `POST /api/services/homeassistant/restart`, danach warten, bis `/api/` wieder antwortet, und im Protokoll
  (`/api/error_log` bzw. Einstellungen → System → Protokolle) nach `tobibox` suchen.
- In HA änderst du **nichts außer** `custom_components/tobibox` und dem Neustart: keine anderen Integrationen, keine
  Automationen, keine Einstellungen. Echte Hörspiele, Tobies und Zuordnungen nicht löschen oder umhängen; zum Testen
  eine eigene Test-Serie und Test-Tobies verwenden und danach aufräumen.

## 5. Git

- Branch `claude/beautiful-sagan-mg11gf`. Vor jeder Arbeit `git pull --rebase`, nach jedem fertigen Schritt committen
  und pushen. Keine Pull-Requests ohne Tobias’ Auftrag. Commit-Nachrichten auf Deutsch.
- Keine echten Namen (Kinder, Partnerin), keine Passwörter, keine Tokens, keine WLAN-Namen im Repo.

## 6. Übergabe

- Die Cloud-Sitzung pusht noch A9/A10 und baut danach an der Seite nichts mehr. Wenn du `git log` siehst, dass A9/A10
  da ist, gehört die Seite dir.
- Halte den Stand in `docs/plan/stueckliste-und-psp.md` aktuell, damit jede spätere Sitzung weiß, wo es steht.
