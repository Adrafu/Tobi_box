# MQTT-Konten für die Boxen einrichten

*   **Status:** Anleitung zu AP 3.5, Entwurf. Noch nicht am Gerät durchgegangen.
*   **Zielgruppe:** Tobias.
*   **Gehört zu:** `docs/designs/box-software.md` (Baustein 4, MQTT-Schnittstelle), `docs/protocol/mqtt-v1.md` (Abschnitt 7, Mosquitto-Rechte, und Themenbaum in Abschnitt 2), `docs/betrieb/tailscale-nas.md` (Abschnitt 9 und 10).
*   **Vorlagen dieses AP:** keine eigenen Dateien. Die Beispieldateien für den Broker (`homeassistant/mosquitto/`) entstehen erst in AP 3.3.

Wo eine Angabe nicht sicher ist, steht **„bitte am Gerät prüfen“**.

## 1. Überblick

*   Der MQTT-Broker ist das Mosquitto-Add-on in HA. Er ist nur über Tailscale erreichbar (Port 1883, siehe `tailscale-nas.md`).
*   **Jede Box hat ein eigenes Konto.** Der Kontoname ist der Box-Name, z. B. `box1` (`box_id` in `tobibox.toml`).
*   Die Konten sind **keine** HA-Administratoren. Sie dürfen nur die Themen aus Abschnitt 3.
*   HA und das Add-on-Standardkonto `addons` bleiben unbeschränkt.
*   Ohne Anmeldung geht nichts: Das Add-on erlaubt **keine anonyme Anmeldung** (laut Add-on-Dokumentation).

## 2. Konten anlegen

Für jede Box ein Konto. Für zwei Boxen: `box1` und `box2`.

1.  Ein Passwort je Box erzeugen. Lang und zufällig, z. B. mit `openssl rand -base64 24` auf dem Mac. Nicht wiederverwenden.
2.  Das Passwort sofort notieren, und zwar **nur** in der Box-Konfiguration (Abschnitt 5) und im Add-on (Abschnitt 4). Nirgends sonst.
3.  Das Konto unter `logins` im Add-on eintragen (Abschnitt 4).

## 3. Rechte je Konto

Die Rechte stehen als Vertrag in `docs/protocol/mqtt-v1.md`, Abschnitt 7. Für `box1` (für `box2` entsprechend):

| Thema | Recht | Warum |
|---|---|---|
| `tobibox/config` | lesen | HA-Konfiguration (Zuordnungen) holen |
| `tobibox/box1/cmd` | lesen | Befehle von HA (Lernen, Sync, Update) |
| `tobibox/box1/unknown/+/ack` | lesen | Bestätigung unbekannter Tobies |
| `homeassistant/status` | lesen | Neustart von HA erkennen |
| `tobibox/box1/online` | schreiben | Erreichbarkeit |
| `tobibox/box1/status` | schreiben | Zustand für Sensoren |
| `tobibox/box1/event` | schreiben | Ereignisse |
| `tobibox/box1/unknown/+` | schreiben | unbekannte Tobies melden (auch löschen) |
| `homeassistant/+/tobibox_box1/+/config` | schreiben | eigene Discovery |

Die Box darf **nicht**: `tobibox/config` schreiben, `…/cmd`, `…/ack` oder `…/ui/…` schreiben, Themen der anderen Box anfassen, Discovery anderer Boxen oder andere Teile unter `homeassistant/` schreiben.

Alternative in einer Regel (mit `%u` = Benutzername): Die Vorlage in `mqtt-v1.md`, Abschnitt 7, zeigt sie. Eine Form genügt. **Bitte am Gerät prüfen**, ob das Add-on die Form `pattern` in seiner Mosquitto-Version annimmt. Im Zweifel die Form mit einer Zeile je Thema nehmen.

## 4. Einstellung im Mosquitto-Add-on (HA)

HA: Einstellungen > Add-ons > Mosquitto broker > Konfiguration. Als YAML (bitte am Gerät prüfen, ob die Oberfläche YAML oder Felder zeigt):

```yaml
logins:
  - username: box1
    password: <Passwort von Box 1>
  - username: box2
    password: <Passwort von Box 2>
customize:
  active: true
  folder: mosquitto
```

*   `customize.active: true` ist nötig, sonst liest das Add-on keine eigene ACL-Datei.
*   Die ACL-Datei liegt unter `/share/mosquitto/`. Die Datei `acl.conf` verweist auf die Regeln (laut Add-on-Dokumentation: `acl_file /share/mosquitto/accesscontrollist`). Die Regeln stehen in `/share/mosquitto/accesscontrollist`, die Form steht in Abschnitt 3. Die Vorlagendatei kommt in AP 3.3 unter `homeassistant/mosquitto/`. Bis dahin von Hand anlegen. **Bitte am Gerät prüfen**, ob die Dateien unter `/share/mosquitto/` mit dem Dateimanager oder über SMB ankommen.
*   Passwort als Hash statt Klartext: Das Add-on kann Hash-Einträge verarbeiten (`password_pre_hashed: true`). Die Erzeugung des Hashs ist bitte am Gerät zu prüfen. Der Hash ist trotzdem geheim, wenn er in Abschnitt 5 nicht steht.
*   Nach jeder Änderung das Add-on **neu starten** und das Protokoll des Add-ons ansehen. Dort stehen Anmeldefehler.

**Wichtig:** `homeassistant` und `addons` dürfen nicht durch die ACL ausgesperrt werden. Die Regeln oben nur für die Box-Konten anlegen und die Standardkonten unbeschränkt lassen. **Bitte am Gerät prüfen**, ob das Add-on die Standardkonten mit `topic readwrite #` benötigt (Dokumentation nennt sie so).

## 5. Box: Zugangsdaten

In `tobibox.toml` auf der Box, **nur dort**. Die Datei steht in `.gitignore`.

```toml
[mqtt]
box_id = "box1"               # Box-Name und zugleich MQTT-Konto
host = "<HA-Name oder Tailscale-IP>"
port = 1883
passwort = "<Passwort>"       # nur auf dieser Box
```

*   Die Schlüsselnamen sind seit AP 3.3 festgelegt (`box/src/tobibox/config.py`, Abschnitt `[mqtt]`). Ein Schlüssel `benutzer` ist nicht nötig: Der Benutzername ist immer `box_id`. Der Dienst meldet Passwort-Schlüssel nie in Protokollen (`eventlog.py` ersetzt sie).
*   Dateirechte auf der Box: nur der Dienstbenutzer darf lesen (`chmod 600`, bitte am Gerät prüfen, welcher Benutzer den Dienst startet).
*   Nie in einen Befehl eintippen, der in der Shell-Historie landet. Lieber mit einem Editor öffnen.

## 6. Konto sperren oder Passwort wechseln

*   **Konto sperren:** Den Eintrag `box1` aus `logins` entfernen, Add-on neu starten. Die Box kann sich dann nicht mehr anmelden. Zusätzlich die Regeln für `box1` aus der ACL-Datei löschen, damit nichts übrig bleibt.
*   **Passwort wechseln:** Neues Passwort erzeugen, im Add-on ändern, Add-on neu starten, in `tobibox.toml` der Box ändern.
*   **Box verloren:** Zuerst Tailscale sperren (`tailscale-nas.md`, Abschnitt 9), dann das MQTT-Konto. Reihenfolge egal, aber beides.
*   Retained-Nachrichten der Box (`tobibox/box1/online`, `unknown/…`) bleiben beim Broker liegen. Beim Sperren eines Kontos leer veröffentlichen oder mit Tobias' Admin-Konto löschen. **Bitte am Gerät prüfen**, mit welchem Werkzeug das geht (z. B. `mosquitto_pub` mit leerer Nutzlast und `-r`).

## 7. Prüfen

Nach Abschnitt 4 und 5 muss eine Box sich anmelden können. Ein einfacher Test
von der Box aus (Paket `mosquitto-clients`, bitte am Gerät prüfen):

```
read -rs -p "Passwort: " PW
mosquitto_sub -h <HA-Name> -p 1883 -u box1 -P "$PW" -t 'tobibox/box1/cmd' -v
unset PW
```

*   Der Test muss sich anmelden und warten, ohne Fehler.
*   Ein Thema außerhalb der Rechte, z. B. `mosquitto_sub -t 'tobibox/box2/cmd'`, muss abgelehnt werden. Bei einem Lesetest kommt der Broker oft nur still zurück. **Bitte am Gerät prüfen**, woran man die Ablehnung erkennt (Add-on-Protokoll).
*   Ein falsches Passwort muss abgelehnt werden.
*   `-P` mit Argument ist auf einer Ein-Benutzer-Box vertretbar, weil es nur kurz im Prozesslisting steht. Keine Passwörter in Dateien mit Beispielen.

Die Box-Software prüft diese Verbindung ausführlicher in AP 3.3 (`box/tests/integration/test_ha_mqtt.py`).

## 8. Bitte am Gerät prüfen

*   Oberfläche des Add-ons: YAML oder Felder (Abschnitt 4).
*   Pfad und Dateinamen unter `/share/mosquitto/` (Abschnitt 4).
*   Erzeugung eines Passwort-Hashs für `password_pre_hashed` (Abschnitt 4).
*   Ob die Standardkonten `homeassistant` und `addons` in der ACL eigene Regeln brauchen (Abschnitt 4).
*   Werkzeug zum Leeren retained-Nachrichten (Abschnitt 6).
*   Wie der Dienst auf der Box läuft und wer `tobibox.toml` liest (Abschnitt 5).
*   Woran eine abgelehnte Anmeldung im Add-on-Protokoll erkennbar ist (Abschnitt 7).

## 9. Was Tobias liefern muss

*   Die Namen der Boxen (`box1`, `box2`), so wie sie in Tailscale und `tobibox.toml` stehen.
*   Ergebnis des Tests aus Abschnitt 7 je Box (ohne Passwort).
*   Die Version des Mosquitto-Add-ons und die von HA (AP 3.1 braucht sie).

## Quellen

*   Home Assistant Mosquitto-Add-on, Dokumentation (logins, customize, acl_file, anonyme Anmeldung nicht unterstützt, Port 1883): https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md
*   Interne Verträge: `docs/protocol/mqtt-v1.md`, Abschnitte 1, 2, 7.
