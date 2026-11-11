# Tailscale, NAS und rsync einrichten

*   **Status:** Anleitung zu AP 3.5, Entwurf. Noch nicht am Gerät durchgegangen.
*   **Zielgruppe:** Tobias. Die Schritte kann nur er ausführen.
*   **Gehört zu:** `docs/designs/box-software.md` (Netz, Sync, Strom; Entscheidung D; Risiken), `docs/plan/stueckliste-und-psp.md` (6.2.3, 6.6).
*   **Vorlagen:** `deploy/tailscale/acl.example.json`, `deploy/nas/rsyncd.example.conf`, `deploy/tailscale/acl-pruefung.sh`, `deploy/tailscale/einrichtung-assistent.sh`.

Wo eine Angabe nicht sicher ist, steht **„bitte am Gerät prüfen“**. Dann
den Text auf dem Bildschirm nehmen, nicht diese Anleitung.

## 1. Überblick

Die Box spricht mit HA und dem NAS **nur über Tailscale**, egal ob Heimnetz
oder Handy-Hotspot. Die Box öffnet keinen Port ins Internet.

```
Box (tag:box) ──► HA-Broker, Port 1883 (tag:ha)     MQTT
Box (tag:box) ──► QNAP, Port 873 (tag:nas)          rsync, nur lesen
HA (tag:ha)   ──► QNAP, Port 445 (tag:nas)          SMB, Schreiben
Tobias (Konto) ──► alles                             Verwaltung
```

Von außen erreichbar ist nur HA über Nabu Casa (Tobias' Handy). Das NAS hat
kein myQNAPcloud und keine Ports im Router.

**Grundsatz:** Was nicht in der ACL steht, ist gesperrt. Die Vorlage ersetzt die
Standardregel von Tailscale. Ohne Ersatz darf jedes Gerät alles erreichen.

## 2. Tailscale-Konto, Tags und ACL

1.  Konto anlegen bzw. prüfen. Admin-Konsole öffnen (bitte am Gerät prüfen: Menü „Access controls“).
2.  Tags brauchen einen Eintrag in `tagOwners`, sonst gelten sie in ACL-Regeln nicht. Die Vorlage legt `tag:box`, `tag:ha` und `tag:nas` an und setzt als Besitzer `tobias@example.com`. **Diesen Wert durch deine Adresse ersetzen.**
3.  Inhalt von `deploy/tailscale/acl.example.json` in die Richtlinie einfügen und speichern. Die Vorlage gilt nur, wenn sie gespeichert ist.
4.  Die Regeln in der Vorlage:
    *   Deine Geräte (`autogroup:member`) erreichen alles. So bleiben Verwaltung und Tests möglich.
    *   Boxen (`tag:box`) erreichen nur `tag:nas:873` (rsync) und `tag:ha:1883` (MQTT).
    *   HA (`tag:ha`) erreicht `tag:nas:445` (SMB, zum Schreiben auf die Freigabe).
    *   Alles andere fehlt, ist also gesperrt.
5.  Hinweis: Tailscale empfiehlt inzwischen „Grants“ statt der alten ACL-Syntax. Die ACL-Form ist weiter dokumentiert und funktioniert. Ob die Konsole sie noch unverändert annimmt, bitte am Gerät prüfen.
6.  Port 445 für HA: Bitte am Gerät prüfen, ob HA die Freigabe über Tailscale oder über das Heimnetz einbindet. Läuft der Verkehr über das Heimnetz, ist die Regel für HA nur Vorsorge.

## 3. QNAP: Tailscale-App und myQNAPcloud

1.  Im App Center die App **Tailscale** installieren (bitte am Gerät prüfen: genauer Name).
2.  Anmelden und das Gerät mit `tag:nas` versehen. Die Tags werden in der Admin-Konsole gesetzt, nicht nur auf dem NAS.
3.  Das NAS erhält so eine feste Tailscale-Adresse. Für rsync und SMB die Adresse oder den Namen aus der Konsole nehmen.
4.  **myQNAPcloud abschalten.** Der Zugriff von außen geht nur über Tailscale. Bitte am Gerät prüfen, wo das in QTS steht (in der Regel unter den Cloud-Diensten).
5.  Das NAS-Admin-Konto mit starkem Passwort und, wenn möglich, Zwei-Faktor-Anmeldung sichern. SSH nur für Tobias, nicht für die Boxen.

## 4. QNAP: rsync-Server

**Gewählte Variante (11.11., Tobias):** Die Boxen holen Medien vom **eingebauten Rsync-Server des QNAP** (Hybrid Backup Sync, HBS 3, Port 873) mit **einem gemeinsamen Konto**. Der Rsync-Server des QNAP kennt keine eigenen Module: Das Modul ist der **Freigabeordner** (hier `tobibox`), die Medien liegen im Unterordner `medien`. In `tobibox.toml` heißt das `modul = "tobibox"` und `pfad = "medien"`; die Box holt von `rsync://<Konto>@<QNAP>:873/tobibox/medien/`.

1.  Rsync-Server aktivieren. Der Pfad ist nicht sicher, bitte am Gerät prüfen. Mögliche Stellen in Hybrid Backup Sync: Seite **Dienste** („Services“), dort der Eintrag „Rsync-Server“. In älteren Versionen ist es „Backup-Server“ > „Rsync-Server“. Die Hilfe am NAS (Suche nach „Rsync“) führt direkt hin.
2.  Port **873** prüfen.
3.  **Ein gemeinsames Konto** für alle Boxen anlegen (Name z. B. `tobibox`) und ihm die Freigabe `tobibox` geben. Das Passwort steht nur auf den Boxen (Abschnitt 10).
4.  Die Freigaben selbst: `tobibox/` mit den Unterordnern `medien/`, `export/`, `releases/` und `medien/_papierkorb/`. Bitte am Gerät prüfen, ob der Rsync-Server Unterordner einer Freigabe so ausliefert (`rsync --list-only rsync://<Konto>@<QNAP>/tobibox/medien/`).
5.  Den Eingang anlegen: `tobibox/eingang/`, **neben** `medien/` (nicht darin). Dort legt Tobias Downloads ab (Hörbücher, Hörspiele). HA sortiert sie nach den Metadaten in `medien/` ein (Entscheidung M). Die Box holt nur `…/tobibox/medien/` und sieht den Eingang nie. Sicherheitsnetz: Die Box schließt `_upload/`, `_papierkorb/` und `eingang/` am Anfang der **Quelle** (also von `medien/`) selbst aus, auch wenn sie dort jemand anlegt (Vertrag W, Abschnitt 12).

**Risiko, bewusst in Kauf genommen:** Das gemeinsame Konto kann per rsync **alle Freigaben lesen und schreiben**, nicht nur `medien/`. Eine verlorene Box ist damit ein Schlüssel zum NAS. Die Box selbst benutzt rsync nur lesend: Quelle ist immer der Server, Ziel immer ein lokaler Pfad, `--delete` wirkt nur auf die Box. Das prüft ein Test, es schützt aber nicht vor einer gestohlenen Box. Ausgleich:

*   Der Rsync-Server ist nur im Heimnetz und über Tailscale erreichbar, nicht aus dem Internet (kein Portforwarding, ACL in Abschnitt 2 und 8).
*   Das Passwort steht nur auf den Boxen (Rechte 600), nicht im Repo.
*   Bei Verlust einer Box das Passwort **sofort am QNAP ändern** und auf der anderen Box neu eintragen; zusätzlich den Tailscale-Schlüssel sperren (Abschnitt 9).

**Rückweg:** Wird das Risiko zu groß, läuft statt des QNAP-Dienstes ein rsync-Container (Docker/Container Station) mit **Nur-Lesen-Modul** und einem Konto je Box (Vorlage `deploy/nas/rsyncd.example.conf`: Modul `medien`, `read only = yes`, `exclude` für `_upload/`, `_papierkorb/`, `eingang/`). Die Box ändert sich dafür nur in der Konfiguration: `modul = "medien"`, kein `pfad`, eigenes Konto je Box.

**Am Mac:** Apples `rsync` (openrsync, Protokoll 29) taugt nicht. Der Dienst bricht beim Start mit einer klaren Meldung ab. `brew install rsync` und in `[sync]` `rsync = "/opt/homebrew/bin/rsync"` eintragen.

Gegenprobe: Von einer Box aus (Abschnitt 8) muss der rsync-Daemon antworten und `--list-only` die Medien zeigen. Mit dem gemeinsamen Konto ist ein Schreibversuch **nicht** gesperrt; deshalb gehört der Schutz in den Umgang mit Passwort und Netz (siehe Risiko).

## 5. HA: Tailscale-Add-on, Freigaben und Rechte

1.  Das Tailscale-Add-on in HA installieren (bitte am Gerät prüfen: Add-on-Name und Anmeldeweg).
2.  Das HA-Gerät mit `tag:ha` versehen (Admin-Konsole).
3.  Die NAS-Freigabe in HA als Netzwerkspeicher einbinden (SMB). Unter Einstellungen > System > Speicher (bitte am Gerät prüfen).
4.  **HA-Rechte auf dem NAS:** HA hat **volles Schreibrecht** auf `tobibox/medien/`, `tobibox/export/`, `tobibox/releases/` und `tobibox/eingang/`. Das ist Entscheidung D: Tobias ist der einzige Benutzer, der Schutz für die Boxen ist die Signatur der Update-Pakete (Stufe 3b). Ein Box-Konto darf dort nichts schreiben.
5.  Tobias legt die Update-Pakete in `releases/` selbst ab (oder über den Export aus HA). Die Box prüft jede Signatur.
6.  Papierkorb: `medien/_papierkorb/` wird von HA beschrieben. Die Boxen übernehmen den Papierkorb nicht.

## 6. Box: Tailscale anmelden

1.  Tailscale auf dem Pi installieren (Anleitung von Tailscale für Linux; bitte am Gerät prüfen).
2.  Auth-Key in der Admin-Konsole erzeugen: **Tag `tag:box`**, **nicht wiederverwendbar**, **Ablauf kurz** (z. B. 1 Tag). Den Key nach dem Anmelden sofort löschen.
3.  Anmelden mit dem Key, z. B. `sudo tailscale up --advertise-tags=tag:box` (bitte am Gerät prüfen: Option und Ablauf des Keys). Der Key wird nie ins Repo oder in einen Befehl gespeichert, der im Verlauf landet. Das Eingeben am Terminal ist in Ordnung.
4.  Prüfen: `tailscale status` zeigt die Box mit Tag `tag:box`.
5.  Der Box-Name in Tailscale muss zu `box_id` in `tobibox.toml` passen (z. B. `box1`).

## 7. Schlüsselablauf abschalten

Tailscale-Schlüssel laufen standardmäßig ab. Läuft der Schlüssel einer Box ab,
fällt sie unbemerkt aus dem Netz. Deshalb für die Box-Knoten aus.

1.  Admin-Konsole, Seite **Machines** („Geräte“). Bei jedem Box-Knoten das Menü rechts öffnen und **Disable key expiry** wählen.
2.  Tagged Geräte haben das laut Tailscale meist schon aus. Trotzdem kontrollieren. Filter „Expiry disabled“ zeigt alle.
3.  Für HA und das NAS ebenso, wenn sie nicht ohnehin getaggt und ausgeschaltet sind (bitte am Gerät prüfen).
4.  **Risiko:** Ein Knoten ohne Ablauf ist dauerhaft offen, bis man ihn entfernt. Deshalb Abschnitt 9 kennen.

## 8. ACL prüfen

Auf **jeder** Box ausführen, nach jeder Änderung an der ACL:

```
NAS_HOST=<NAS-Name oder Tailscale-IP> \
HA_HOST=<HA-Name oder Tailscale-IP> \
GESPERRT="<NAS-Name>:22 <NAS-Name>:8080 <HA-Name>:8123 <box2-Name>:22" \
  bash deploy/tailscale/acl-pruefung.sh
```

*   `NAS_HOST` und `HA_HOST` müssen erreichbar sein (Ports 873 und 1883).
*   In `GESPERRT` alle anderen Ziele nennen, die **nicht** erreichbar sein sollen: NAS-SSH, NAS-Weboberfläche, HA-Weboberfläche (8123), die andere Box.
*   Ein gesperrtes Ziel kann auch offline sein. Deshalb zählt das Ergebnis nur zusammen mit den erreichbaren Zielen.

Ergebnis: Exitcode 0 und „ACL wie erwartet“. Bei einem Befund: die ACL-Datei
prüfen (Abschnitt 2), dann Tailscale neu prüfen lassen.

Alternativ führt `deploy/tailscale/einrichtung-assistent.sh` durch alle Schritte
und fragt bei jedem nach, ob er erledigt ist.

## 9. Schlüssel einer verlorenen Box sperren

Eine Box ist verloren oder wurde verkauft, oder ihr Schlüssel ist unbekannt.

1.  **Tailscale:** In der Admin-Konsole den Box-Knoten **entfernen** (Machines, Menü, Remove). Dann erreicht die Box weder HA noch NAS. Bitte am Gerät prüfen: Menüpunkt.
2.  **Auth-Keys** unter den Schlüsseln prüfen und jeden offenen Key der Box widerrufen.
3.  **MQTT:** Das Konto der Box im Mosquitto-Add-on löschen oder das Passwort ändern und das Add-on neu starten (`mqtt-konten.md`, Abschnitt 6).
4.  **rsync:** Das rsync-Konto der Box auf dem QNAP sperren oder löschen (Abschnitt 4).
5.  Danach ist die Box nutzlos für das System. Eine wiedergefundene Box bekommt nach Abschnitt 6 einen neuen Knoten und neue Konten.

## 10. Passwörter

*   Passwörter der Box-Konten (MQTT und rsync) stehen **nur auf der Box** in `tobibox.toml`. Diese Datei ist in `.gitignore` und wird nie committet.
*   Das MQTT-Passwort braucht der Broker auch. Es steht deshalb zusätzlich im Mosquitto-Add-on auf HA (Einstellungen des Add-ons, nicht im Repo). Das ist der einzige zweite Ort.
*   Ein Tailscale-Auth-Key ist nach dem Anmelden verbraucht. Nicht aufbewahren.
*   Das NAS-Admin-Passwort und das Tailscale-Konto liegen nur bei Tobias.
*   Keine Passwörter in dieser Anleitung, in Skripten oder im Verlauf von Befehlen. Die Vorlagen enthalten nur Platzhalter.

## 11. Bitte am Gerät prüfen

*   Menüpfad und Name des Rsync-Servers in QTS / Hybrid Backup Sync (Abschnitt 4).
*   Name der Tailscale-App im App Center (Abschnitt 3).
*   Lage von myQNAPcloud in QTS (Abschnitt 3).
*   Option für `tailscale up` mit Tag und Ablauf des Keys (Abschnitt 6).
*   Name des Tailscale-Add-ons in HA und Weg zur Anmeldung (Abschnitt 5).
*   Ob HA die NAS-Freigabe über Tailscale oder über das Heimnetz einbindet (Abschnitt 2, Schritt 6).
*   Menüpunkt „Remove“ und Widerruf der Auth-Keys in der Admin-Konsole (Abschnitt 9).
*   Ob die Konsole die ACL-Datei in der bisherigen Form annimmt; Tailscale empfiehlt Grants (Abschnitt 2, Schritt 5).

## 12. Was Tobias liefern muss

*   Tailscale-Kontoname (E-Mail) für `tagOwners`.
*   Namen der Geräte: NAS, HA, Box 1, Box 2 (in Tailscale).
*   Namen der NAS-Freigabe und den Pfad `tobibox/` darin.
*   Ergebnis von `acl-pruefung.sh` auf jeder Box (Ausgabe kopieren, ohne Passwörter).
*   Bestätigung, dass myQNAPcloud aus ist und Key expiry für die Box-Knoten aus.

## Quellen für die Menü- und Befehlsangaben

*   Tailscale, Syntax der Richtlinie (tagOwners, acls, Tags): https://tailscale.com/docs/reference/syntax/policy-file
*   Tailscale, Tags: https://tailscale.com/docs/features/tags
*   Tailscale, Schlüsselablauf (Disable Key Expiry, getaggte Geräte): https://tailscale.com/docs/features/access-control/key-expiry
*   Tailscale, Grants (Empfehlung): https://tailscale.com/docs/reference/examples/grants
*   Home Assistant Mosquitto-Add-on (logins, customize, acl_file, Port 1883): https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md
*   QNAP, Hybrid Backup Sync (Dienste): https://www.qnap.com/en/how-to/tutorial/article/hbs-hybrid-backup-sync-quick-start-guide
