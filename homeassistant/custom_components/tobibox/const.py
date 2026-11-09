"""Konstanten der Integration ``tobibox`` (Vertrag W, ``docs/protocol/ha-websocket-v1.md``)."""

from __future__ import annotations

import re
from typing import Final

DOMAIN: Final = "tobibox"

#: Vertragsversion (``hello.v``, jedes Ereignis, jede Upload-Antwort)
VERTRAG_V: Final = 1

# --- Einrichtung (config_flow) ---------------------------------------------
CONF_MEDIEN_PFAD: Final = "medien_pfad"
CONF_BOXEN: Final = "boxen"
CONF_UPLOAD_MAX_MIB: Final = "upload_max_mib"
UPLOAD_MAX_MIB_VORGABE: Final = 500

# --- Ordner neben ``medien/`` (Vertrag W, 11.1) -------------------------------
ORDNER_EINGANG: Final = "eingang"
ORDNER_EXPORT: Final = "export"
ORDNER_RELEASES: Final = "releases"
ORDNER_PAPIERKORB: Final = "_papierkorb"
ORDNER_UPLOAD: Final = "_upload"
EXPORT_DATEI: Final = "config.json"
SERIE_JSON: Final = "serie.json"

# --- Audioformate (D5, ``data-model.md`` Abschnitt 5) --------------------------
ENDUNGEN: Final = ("mp3", "m4a", "m4b", "aac", "flac", "ogg", "opus", "wav")

#: erzwungenes Eingabeformat von ``ffprobe`` je Endung (Vertrag W, 5.4)
FORMAT_JE_ENDUNG: Final = {
    "mp3": "mp3",
    "m4a": "mov,mp4,m4a,3gp,3g2,mj2",
    "m4b": "mov,mp4,m4a,3gp,3g2,mj2",
    "aac": "aac",
    "flac": "flac",
    "ogg": "ogg",
    "opus": "ogg",
    "wav": "wav",
}

#: erlaubte ``format_name`` im Ergebnis von ``ffprobe`` (Teilmengen der erzwungenen Formate)
ERLAUBTE_FORMATNAMEN: Final = frozenset(
    {"mp3", "mov", "mp4", "m4a", "3gp", "3g2", "mj2", "aac", "flac", "ogg", "wav"}
)

FFPROBE_ZEITLIMIT_S: Final = 30
FFPROBE_SPEICHER_BYTES: Final = 1024**3

# --- Grenzen (Vertrag W, Abschnitt 8) ------------------------------------------
UPLOAD_BLOCK_BYTES: Final = 1048576
UPLOAD_PARALLEL: Final = 2
UPLOAD_RESERVE_BYTES: Final = 100 * 1024 * 1024
UPLOAD_ERGEBNIS_MERKEN_S: Final = 3600
UPLOAD_ERGEBNIS_ANZAHL: Final = 100
UPLOAD_SAMMELZEIT_S: Final = 20
PART_MAX_ALTER_S: Final = 24 * 3600

SERIE_NAME_MAX: Final = 100
FOLGE_ANZEIGE_MAX: Final = 200
TOBIE_NAME_MAX: Final = 60
NAME_MAX_BYTES: Final = 255
LIMIT_MAX: Final = 100
LIMIT_MAX_GROSS: Final = 200
KONFIG_MAX_BYTES: Final = 256 * 1024

EINGANG_RUHE_S: Final = 120
EINGANG_STILLE_S: Final = 30
EINGANG_NACHPLAN_S: Final = 60
EINGANG_TIEFE_MAX: Final = 5
EINGANG_PROTOKOLL_MAX: Final = 100
INDEX_MAX: Final = 20000
PRUEF_INTERVALL_S: Final = 600

ANFRAGE_ID_ANZAHL: Final = 100
ANFRAGE_ID_DAUER_S: Final = 600

# --- Konfiguration (``data-model.md`` Abschnitt 2) -----------------------------
SCHEMA_KONFIG: Final = 2
LESEZEICHEN_TAGE_VORGABE: Final = 14
LESEZEICHEN_TAGE_MAX: Final = 365
STANDARD_ZEITZONE: Final = "Europe/Berlin"
START_WARTEZEIT_S: Final = 15.0
PUBACK_ZEITLIMIT_S: Final = 5.0
EXPORT_WIEDERHOLUNG_S: Final = (10.0, 60.0, 300.0)
EXPORT_WIEDERHOLUNG_DANACH_S: Final = 900.0

# --- Lernmodus (Vertrag W, 3.6 und 6.2) ----------------------------------------
LERN_BEFEHL_TTL_S: Final = 60
LERN_ABBRUCH_TTL_S: Final = 30
SYNC_TTL_S: Final = 300
UPDATE_TTL_S: Final = 300
LERN_FRIST_S: Final = 180
LERN_KEIN_STATUS_S: Final = 30
LERN_RUECKFRAGE_MIN_S: Final = 60
LERN_VERLAUF_MAX: Final = 20
BOX_EREIGNISSE_MAX: Final = 20

# --- Bündeln von Ereignissen (Vertrag W, Abschnitt 4) ----------------------------
EREIGNIS_BUENDEL_S: Final = 1.0

# --- Muster ----------------------------------------------------------------
RE_BOX: Final = re.compile(r"^[a-z0-9][a-z0-9_-]{1,23}$")
RE_UID: Final = re.compile(r"^(?:[0-9a-f]{8}|[0-9a-f]{14}|[0-9a-f]{16}|[0-9a-f]{20})$")
RE_LISTE_ID: Final = re.compile(r"^[0-9a-f]{16}$")
RE_ID12: Final = re.compile(r"^[0-9a-f]{12}$")
RE_UPLOAD_ID: Final = re.compile(r"^[0-9A-Za-z-]{8,64}$")
RE_ANFRAGE_ID: Final = RE_UPLOAD_ID

#: Fähigkeiten der Stufe 3a (``hello.faehigkeiten``)
FAEHIGKEITEN: Final = (
    "medien",
    "upload",
    "zuordnung",
    "tobie_namen",
    "neue_tobies",
    "lernmodus",
    "boxen",
    "papierkorb",
    "liste_ausrollen",
    "konfig_export",
    "sync",
    "eingang",
    "korrektur",
    "serie_loeschen",
)

# --- MQTT-Themen (``mqtt-v1.md`` Abschnitt 2) ----------------------------------
THEMA_CONFIG: Final = "tobibox/config"
THEMA_HA_STATUS: Final = "homeassistant/status"

# --- Ereignisthemen (Vertrag W, Abschnitt 4) -----------------------------------
EREIGNIS_THEMEN: Final = (
    "boxen",
    "neue_tobies",
    "lernmodus",
    "medien",
    "eingang",
    "konfig",
    "upload",
)

# --- Namen reserviert ----------------------------------------------------------
GERAETENAMEN: Final = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
)
