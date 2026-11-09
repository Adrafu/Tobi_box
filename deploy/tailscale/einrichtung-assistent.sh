#!/usr/bin/env bash
# Schritt-für-Schritt-Begleitung für die Einrichtung (AP 3.5, optional).
#
# Das Skript ändert nichts am System und fragt keine Passwörter oder Schlüssel ab.
# Es führt durch die Schritte aus docs/betrieb/tailscale-nas.md und
# docs/betrieb/mqtt-konten.md und fragt nach, ob jeder Schritt erledigt ist.
#
# Aufruf: bash deploy/tailscale/einrichtung-assistent.sh
# Antworten: j = erledigt, n = nochmal anzeigen, s = überspringen, q = beenden.

set -u

if [ ! -t 0 ]; then
    echo "Dieses Skript braucht ein Terminal (interaktiv)." >&2
    exit 2
fi

SKRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DOKU="$SKRIPT_DIR/../../docs/betrieb"

SCHRITTE=(
    "1|Tailscale-Konto und Tags|Admin-Konsole öffnen. Unter Access controls die Datei aus deploy/tailscale/acl.example.json einfügen. Platzhalter tobias@example.com ersetzen. Speichern, dann acl-pruefung.sh später prüfen.|tailscale-nas.md, Abschnitt 2"
    "2|QNAP: Tailscale-App|Tailscale aus dem App Center installieren, anmelden, Gerät mit tag:nas versehen.|tailscale-nas.md, Abschnitt 3"
    "3|QNAP: rsync-Server|Rsync-Server aktivieren (Pfad am Gerät prüfen). Module medien und releases, beide nur lesend. Ein Konto je Box.|tailscale-nas.md, Abschnitt 4"
    "4|QNAP: myQNAPcloud aus|myQNAPcloud-Zugriff abschalten. Bitte am Gerät prüfen, wo das in QTS steht.|tailscale-nas.md, Abschnitt 3"
    "5|HA: Tailscale-Add-on|Add-on installieren, anmelden, Gerät mit tag:ha versehen. Bitte am Gerät prüfen: Add-on-Name.|tailscale-nas.md, Abschnitt 5"
    "6|HA: Mosquitto-Konten|Add-on-Optionen: logins je Box, customize aktiv, ACL-Datei. Keine Administratoren.|mqtt-konten.md, Abschnitte 2 bis 4"
    "7|HA: Freigaben einbinden|Netzwerkspeicher auf die NAS-Freigabe mit Schreibrecht für medien/, export/, releases/.|tailscale-nas.md, Abschnitt 5"
    "8|Box: Tailscale und Tag|Tailscale installieren, mit einem Auth-Key als tag:box anmelden. Key nur einmal, nicht wiederverwendbar.|tailscale-nas.md, Abschnitt 6"
    "9|Box: Schlüsselablauf aus|In der Admin-Konsole für den Box-Knoten Key expiry deaktivieren (Tagged-Geräte meist schon aus, bitte prüfen).|tailscale-nas.md, Abschnitt 7"
    "10|Box: Zugangsdaten|Passwörter nur in tobibox.toml auf der Box eintragen, nie im Repo.|mqtt-konten.md, Abschnitt 5"
    "11|Box: ACL prüfen|acl-pruefung.sh auf der Box ausführen. Muss ohne Befund durchlaufen.|tailscale-nas.md, Abschnitt 8"
)

OFFEN=()

zeige_schritt() {
    local nr="$1" titel="$2" text="$3" fundstelle="$4"
    echo
    echo "=== Schritt $nr: $titel ==="
    echo "$text"
    echo "Anleitung: $DOKU/$fundstelle"
}

for eintrag in "${SCHRITTE[@]}"; do
    IFS='|' read -r nr titel text fundstelle <<< "$eintrag"
    while true; do
        zeige_schritt "$nr" "$titel" "$text" "$fundstelle"
        read -r -p "Erledigt? [j/n/s/q] " antwort
        case "$antwort" in
            j|J) break ;;
            s|S) OFFEN+=("$nr $titel"); break ;;
            n|N) continue ;;
            q|Q) echo "Abgebrochen. Offen bleibt alles ab Schritt $nr."; exit 0 ;;
            *) echo "Bitte j, n, s oder q eingeben." ;;
        esac
    done
done

echo
if [ "${#OFFEN[@]}" -gt 0 ]; then
    echo "Übersprungen (bitte nachholen):"
    printf '  - %s\n' "${OFFEN[@]}"
else
    echo "Alle Schritte als erledigt markiert."
fi

echo
read -r -p "Jetzt acl-pruefung.sh auf dieser Box starten? [j/n] " start
if [ "$start" = "j" ] || [ "$start" = "J" ]; then
    read -r -p "NAS_HOST (Name oder Tailscale-IP): " nas
    read -r -p "HA_HOST (Name oder Tailscale-IP): " ha
    read -r -p "GESPERRT (Ziele mit Leerzeichen getrennt, host:port): " gesperrt
    NAS_HOST="$nas" HA_HOST="$ha" GESPERRT="$gesperrt" bash "$SKRIPT_DIR/acl-pruefung.sh"
fi
