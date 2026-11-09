#!/usr/bin/env bash
# Prüft auf einer Box, ob die Tailscale-ACL stimmt (AP 3.5).
#
# Erwartung: Die Box erreicht die NAS-Freigabe (rsync, Port 873) und den
# MQTT-Broker in HA (Port 1883). Alle anderen angegebenen Ziele sind gesperrt.
#
# Aufruf auf der Box (Namen oder Tailscale-IPs; keine Passwörter):
#   NAS_HOST=qnap HA_HOST=ha GESPERRT="qnap:22 qnap:8080 ha:8123 box2:22" \
#     bash deploy/tailscale/acl-pruefung.sh
#
# Hinweis: Ein gesperrtes Ziel kann auch offline sein. Deshalb prüft das Skript
# zuerst, ob die erlaubten Ziele erreichbar sind. Ist eines davon nicht
# erreichbar, ist das Ergebnis nicht aussagekräftig.
#
# Exitcode: 0 = alles wie erwartet, 1 = mindestens ein Befund, 2 = Aufruffehler.

set -u

NAS_HOST="${NAS_HOST:-}"
HA_HOST="${HA_HOST:-}"
GESPERRT="${GESPERRT:-}"
ZEITLIMIT_S="${ZEITLIMIT_S:-4}"

if [ -z "$NAS_HOST" ] || [ -z "$HA_HOST" ]; then
    echo "Fehler: NAS_HOST und HA_HOST müssen gesetzt sein." >&2
    echo "Beispiel: NAS_HOST=qnap HA_HOST=ha GESPERRT=\"qnap:22 ha:8123\" $0" >&2
    exit 2
fi

if ! command -v timeout >/dev/null 2>&1; then
    echo "Fehler: 'timeout' fehlt (Paket coreutils)." >&2
    exit 2
fi

# Verbindet per TCP-Verbindungsaufbau (bash /dev/tcp). Gibt 0 zurück, wenn der
# Aufbau gelingt. Host und Port werden als Argumente übergeben, nie in den Code eingesetzt.
erreichbar() {
    timeout "$ZEITLIMIT_S" bash -c 'exec 3<>"/dev/tcp/$1/$2"' _ "$1" "$2" 2>/dev/null
}

FEHLER=0

pruefe_erlaubt() {
    local ziel="$1" ; local host="${ziel%:*}" ; local port="${ziel##*:}"
    if erreichbar "$host" "$port"; then
        echo "OK      erlaubt, erreichbar: $host:$port"
    else
        echo "FEHLER  erlaubt, aber NICHT erreichbar: $host:$port"
        echo "        Prüfen: Gerät an? Tag korrekt? ACL-Regel gespeichert?"
        FEHLER=1
    fi
}

pruefe_gesperrt() {
    local ziel="$1" ; local host="${ziel%:*}" ; local port="${ziel##*:}"
    if erreichbar "$host" "$port"; then
        echo "FEHLER  gesperrt, aber ERREICHBAR: $host:$port"
        echo "        Die ACL lässt mehr zu als erlaubt. Regeln prüfen."
        FEHLER=1
    else
        echo "OK      gesperrt: $host:$port"
    fi
}

echo "== Erlaubte Ziele (müssen erreichbar sein) =="
pruefe_erlaubt "$NAS_HOST:873"
pruefe_erlaubt "$HA_HOST:1883"

echo
echo "== Gesperrte Ziele (dürfen NICHT erreichbar sein) =="
if [ -z "$GESPERRT" ]; then
    echo "HINWEIS  GESPERRT ist leer. Keine Gegenprobe. Mindestens angeben:"
    echo "         NAS-SSH, NAS-Weboberfläche, HA-Weboberfläche, andere Box."
    FEHLER=1
else
    for ziel in $GESPERRT; do
        pruefe_gesperrt "$ziel"
    done
fi

echo
if [ "$FEHLER" -eq 0 ]; then
    echo "Ergebnis: ACL wie erwartet."
    exit 0
fi
echo "Ergebnis: Befunde gefunden. Siehe docs/betrieb/tailscale-nas.md, Abschnitt 8."
exit 1
