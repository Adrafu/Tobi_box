# Goldfisch-Prüfung „ohne V3“ — Rohbefunde

Ziel: `pivot_ohne_v3.md`. Zwei Goldfische ohne Gesprächsverlauf.

## Wartbarkeit (structural, Sonnet)

Urteil: (a) eigene Python-App auf MPD ist über Jahre tragfähiger, wenn der Umfang schriftlich begrenzt wird. Die Hauptlast (Kern, Update/Rückfall, NAS-Weg) ist bei (a) und (b) gleich.

1. Blocker — NAS nie direkt aus dem Internet (QNAP: Qlocker, DeadBolt). VPN mit einem Peer pro Box, ACL nur auf Medienordner, NAS-Konto nur lesend, Schlüssel pro Box widerrufbar; Betriebspflichten (Schlüssel erneuern, Zustand „VPN fehlt“). Tailscale (wenig Wartung, Drittanbieter) vs. QVPN/WireGuard (Port am Router, Handarbeit).
2. Blocker — Update/Rückfall ist die eigentliche Langzeitlast; Paket atomar, Wächter, SD-Image pro Box als Notweg ohne Netz; jährliches neues OS-Image statt „nie“.
3. Major — V3-Pin ist Einfrieren; ohne Spiegel (Fork, Wheel-Cache, Image) in 2–3 Jahren nicht mehr installierbar.
4. Major — Bei (a) liegt die Last in den Randfällen der nachgebauten Funktionen (Lautstärke, Timer, Leerlauf, MPD-Neustart, DB-Neuaufbau nach Sync, Installationsskript). Feste Liste nachbauen/entfällt, Tests gegen echtes MPD, MPD nur über ein dünnes Modul.
5. Major — Bei (b) drei Wahrheiten (`cards.yaml`, Kern, `music_player_status.json`).
6. Major — Ein-Personen-Projekt: Betriebshandbuch mit Wiederherstellung von Null, „was ist wo konfiguriert“, gepinnte Versionen.
7. Major — Box spielt vollständig ohne HA und Netz; MQTT-Themen mit Schema und Discovery; lokaler Notweg (Konfigdatei + SSH / Admin-Befehl).
8. Major — „Läuft am Mac“ darf keine Scheinsicherheit werden: Prüfliste am echten Pi, Konfig Mac/Pi ohne Codeverzweigung.
9. Major — Zwei Boxen: gleiches Paket, Version und Medienstand an HA, Kartentausch ≤ 30 min; Aufräumen alter Folgen.
10. Nit — Ausstiegskriterium in Zahlen fehlt.
