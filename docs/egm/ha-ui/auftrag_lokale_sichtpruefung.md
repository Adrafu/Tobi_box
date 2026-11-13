# Auftrag für eine Claude-Sitzung auf Tobias’ Mac: Sichtprüfung der neuen HA-Seite

Diesen Text als erste Nachricht in eine **lokale** Claude-Sitzung (Claude-Desktop-App oder `claude` im Terminal im
Ordner `~/Tobi_box`) kopieren. Die Sitzung in der Cloud kann Tobias’ Browser und Home Assistant nicht sehen.

---

Du hilfst bei der Abnahme der neuen Home-Assistant-Seite „Tobi Box“. Lies zuerst `CLAUDE.md` im Repo `~/Tobi_box`
(Branch `claude/beautiful-sagan-mg11gf`, vorher `git pull`). Sprache: Deutsch, einfach und direkt. Keine echten Namen
ins Repo schreiben.

**Hintergrund**
- Design: `docs/designs/ha-oberflaeche.md`, Entscheidungen: `docs/egm/ha-ui/resolve.md` (unten „Abnahme A-1a“).
- Code der Seite: `homeassistant/custom_components/tobibox/frontend/` (`tobibox-app.js`, `seiten/*.js`,
  `bausteine.js`, `texte.js`). In HA unter `/tobibox` (nur Administratoren). Testpanel unter `/tobibox-test`.
- In der Cloud gibt es ein Prüfskript mit Testdaten (`homeassistant/tests/frontend/browser/pruefe_seite.py`). Dort sah
  die Seite anders aus als bei Tobias. Genau diesen Unterschied sollst du finden.

**Auftrag**
1. Öffne Tobias’ Home Assistant im Browser (er sagt dir die Adresse und meldet sich selbst an; frag nicht nach
   Passwörtern). Seite „Tobi Box“ öffnen.
2. Sieh dir an: Start, Bibliothek, Suche, eine Serienseite, Geräte (mit Abends), Technik. Jeweils bei schmalem Fenster
   (Handy-Breite, ca. 390 px) und breitem Fenster (Desktop). Mach Screenshots.
3. Tobias meldet: „Ich komm nicht auf die Menüpunkte“ (die Reiter Start · Bibliothek · Tobies · Geräte reagieren nicht
   oder sind nicht erreichbar) und „Desktop schaut nicht gut aus“. Finde heraus, **woran es liegt**: z. B. ob die Reiter
   verdeckt sind, außerhalb des sichtbaren Bereichs liegen, Klicks abgefangen werden, die Seite eine alte Fassung aus dem
   Cache lädt (Versionsnummer im Skript-Pfad `?v=` prüfen), oder ob HA-Elemente (Kopfleiste, Seitenleiste, Safe-Area)
   anders sind als angenommen. Nutze die Entwicklerwerkzeuge (Elemente, Konsole, Netzwerk).
4. **Nichts am Code ändern.** Schreib die Befunde mit Screenshots-Beschreibung, Ursache (belegt oder Vermutung) und
   Vorschlag in die neue Datei `docs/egm/ha-ui/abnahme_a1a_lokal.md`. Konsolenfehler wörtlich übernehmen.
5. Nur diese eine Datei committen (Nachricht „Abnahme A-1a: Befunde der lokalen Sichtprüfung“), vorher
   `git pull --rebase`, dann auf `claude/beautiful-sagan-mg11gf` pushen. Sag Tobias danach Bescheid, dass er der
   Cloud-Sitzung „Befunde liegen in abnahme_a1a_lokal.md“ schreiben soll.
