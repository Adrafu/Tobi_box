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
#: Optionen: Anzeigenamen der Boxen (``box1=Box 1, box2=Box 2``), gespeichert als ``{"box1": "Box 1", …}`` (Vertrag W, 14.9)
CONF_BOX_ANZEIGEN: Final = "box_anzeigen"
#: Optionen: ``ai_task``-Entität für den Claude-Schritt der Online-Suche; leer = Schritt aus (Design Online-Suche 9.2)
CONF_ONLINE_KI_ENTITAET: Final = "online_ki_entitaet"
#: Höchstlänge eines Anzeigenamens einer Box (Zeichen)
BOX_ANZEIGE_MAX: Final = 40
#: 2 GiB je Datei (Vertrag W, 8 und 14.10); bestehende Einträge mit 500 hebt die Migration an
UPLOAD_MAX_MIB_VORGABE: Final = 2048
#: der alte Vorgabewert, den die Migration (Version 2 des Konfigurationseintrags) anhebt
UPLOAD_MAX_MIB_ALT: Final = 500

# --- Ordner neben ``medien/`` (Vertrag W, 11.1) -------------------------------
ORDNER_EINGANG: Final = "eingang"
ORDNER_EXPORT: Final = "export"
ORDNER_RELEASES: Final = "releases"
#: Ordner der Hörkopien auf der Freigabe, **neben** ``medien/`` (Vertrag W, 14.8)
ORDNER_HOERKOPIEN: Final = "hoerkopien"
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
#: Reserve auf der Freigabe (Vertrag W, 5.1 und 14.10): 2 GiB; angekündigte, noch nicht geschriebene Bytes laufender Uploads werden vom freien Platz abgezogen
UPLOAD_RESERVE_BYTES: Final = 2 * 1024**3
UPLOAD_ERGEBNIS_MERKEN_S: Final = 3600
UPLOAD_ERGEBNIS_ANZAHL: Final = 100
UPLOAD_SAMMELZEIT_S: Final = 20
#: Upload mit Wunsch (Vertrag W, 14.4): Ziele, Höchstzahl der Dateien einer Gruppe, Ruhezeit einer unvollständigen Gruppe
WUNSCH_ZIELE: Final = ("auto", "neu", "ergaenzen", "einzeln")
WUNSCH_NAME_MAX_BYTES: Final = 400
GRUPPE_ANZAHL_MAX: Final = 200
GRUPPE_RUHE_MAX_S: Final = 1800
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
#: ``eingang/list``: so viele Dateinamen höchstens je Eintrag (Vertrag W, 3.9); die übrigen zählt ``dateien_weitere``
DATEINAMEN_MAX: Final = 50
INDEX_MAX: Final = 20000
PRUEF_INTERVALL_S: Final = 600
#: Papierkorb (data-model 9, Vertrag W Nr. 12 „Automatik“, BB1): so viele Tage nach ``geloescht_am`` löscht die Integration einen Eintrag endgültig
PAPIERKORB_TAGE: Final = 30
#: Der Lauf „kurz nach dem Start“ (Sekunden nach dem Start der Integration); danach einmal am Tag
PAPIERKORB_START_S: Final = 120

# --- Schutz für Nicht-Administratoren (Vertrag W, 2.4 und 14.10) -----------------
AENDERUNGEN_JE_MINUTE: Final = 30
PAPIERKORB_AKTIONEN_JE_10_MIN: Final = 20
#: „Anders einsortieren“ (Befehl 43, Vertrag W, 2.4): nur Einträge „bitte ansehen“ oder höchstens so alt (seit ``fertig_am``)
EINSORTIERUNG_NEU_ALTER_MAX_S: Final = 24 * 3600
UPLOAD_BYTES_JE_STUNDE: Final = 16 * 1024**3
KONFIG_STAENDE_ANZAHL: Final = 10

# --- Warteschlange „nächster neuer Tobie“ (Vertrag W, 3.13 und 14.10; seit 13.11.) -----------------
#: Vormerkungen zugleich, über alle Boxen (Design 5.13)
WARTESCHLANGE_MAX: Final = 5
#: je Benutzer, für ``warteschlange/set`` und ``warteschlange/abbrechen`` zusammen (nicht für Administratoren)
WARTESCHLANGE_AENDERUNGEN_JE_MINUTE: Final = 30

# --- Bibliothek: Art, Suche, Blättern (Vertrag W, 14.2) -----------------------------
ARTEN: Final = ("hoerspiel", "hoerbuch", "musik", "geschichte")
#: ``online`` = von der Online-Suche übernommen (Vertrag W, 14.2)
ART_QUELLEN: Final = ("tags", "geraten", "manuell", "online")
ART_VORGABE: Final = "hoerspiel"
#: ``favorit`` (Stufe B, Fähigkeit ``favoriten``): nur Einträge mit Stern
FILTER_WERTE: Final = ("ohne_tobie", "neu", "pruefen", "sammlung", "einzeln", "favorit")
#: ``serien/list`` kennt dazu ``online_vorschlag`` (Vertrag W, 14.2; nur Administratoren, nur mit Fähigkeit ``online_suche``)
FILTER_WERTE_SERIEN: Final = (*FILTER_WERTE, "online_vorschlag")
#: ``zuletzt_gehoert`` und ``meist_gehoert`` (Stufe B, Fähigkeit ``gehoert``; ohne Hördaten gilt die Reihenfolge nach Name)
SERIEN_SORTIERUNGEN: Final = ("name", "neu", "angehoert", "zuletzt_gehoert", "meist_gehoert")
FOLGEN_SORTIERUNGEN: Final = ("titel", "neu")
SUCHTEXT_MIN: Final = 2
SUCHTEXT_MAX: Final = 100
SERIEN_LIMIT_MAX: Final = 200
FOLGEN_LIMIT_MAX: Final = 100
FOLGEN_LIMIT_VORGABE: Final = 60
#: Filter ``neu``: Einträge, die in den letzten so vielen Tagen angelegt wurden (Design 5.2)
NEU_TAGE: Final = 14
#: ``serien/list`` ohne ``limit``: so viele Einträge höchstens (``None`` = alle, wie bis 11.11.; Vertrag W, 14.2)
SERIEN_OHNE_LIMIT_MAX: Final = None
#: Art-Vorschlag (Vertrag W, 14.2): „viele“ Tracks, „kurz“ (Mittel unter 8 Minuten), Einzeldatei „unter 30 Minuten“
ART_VIELE_TRACKS: Final = 5
ART_KURZE_TRACKS_MITTEL_S: Final = 8 * 60
ART_GESCHICHTE_MAX_S: Final = 30 * 60

# --- Cover (Vertrag W, 14.3 und 14.10) -------------------------------------------------
COVER_UPLOAD_MAX_BYTES: Final = 3 * 1024**2
COVER_KANTE_MAX_PX: Final = 2048
#: Bilder aus Tags und mitgelieferten Dateien (Modus ``nachsichtig``): Obergrenze der Pixelzahl aus dem Kopf, vor dem Dekodieren.
#: 3000 × 3000 (9 Mio.) geht durch, eine Pixelbombe wie 30 000 × 30 000 nicht. Größere Kanten werden verkleinert und mittig quadratisch zugeschnitten.
COVER_NACHSICHT_PIXEL_MAX: Final = 16_000_000
#: Quadrat bis auf 2 % (Unterschied der Seiten, bezogen auf die längere)
COVER_QUADRAT_TOLERANZ: Final = 0.02
COVER_GROSS_PX: Final = 512
COVER_KLEIN_PX: Final = 192
COVER_JE_STUNDE: Final = 20
COVER_SUCHE_ZEITGRENZE_S: Final = 20
#: Lesen aus den Tags: höchstens so viele Dateien je Eintrag (Schutz vor 300 Aufrufen von ``ffmpeg`` bei einem Eintrag ohne Bild)
COVER_SUCHE_DATEIEN_MAX: Final = 5
COVER_JPEG_QUALITAET: Final = 85
#: Namen im Serien-Ordner (``data-model.md``, Abschnitt 5): automatisch, Foto aus der Seite; als Quelle gelesen, nie geschrieben
COVER_AUTO: Final = "cover.jpg"
COVER_EIGEN: Final = "cover-eigen.jpg"
COVER_QUELLEN: Final = ("folder.jpg", "cover.png")
#: Cover aus der Online-Suche (Design 7.2, ``data-model.md`` 5). Vorrang ``cover-eigen.jpg`` vor ``cover-online.jpg`` vor ``cover.jpg``
COVER_ONLINE: Final = "cover-online.jpg"
#: Zwischenspeicher der kleinen Ansicht (192 px, rund 15 KiB): so viele Bilder höchstens
COVER_KLEIN_CACHE_ANZAHL: Final = 256

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

#: Fähigkeiten (``hello.faehigkeiten``): Stufe 3a, dazu AP 4.7 und die Erweiterungen v1.1
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
    # AP 4.7 und Erweiterungen v1.1 (09.11., Vertrag W, Abschnitt 10)
    "einstellungen",
    "eingang_entfernen",
    "zuordnung_uid",
    "konfig_lesen",
    "upload_fertig_details",
    # Stufe A der HA-Oberfläche (12.11., Vertrag W, 14.1): nur, was das Backend schon liefert
    "konfig_staende",
    # A3: Art, Suche, Filter, Blättern, Befehle 37 und 38, ``text``/``neu`` bei ``zuordnung/list``, ``erwartet_revision`` (A1)
    "bibliothek",
    # A3d: Upload-Felder ``ziel``, ``art``, ``name``, ``gruppe_anzahl``; A3e: dazu Befehl 43 ``einsortierung/neu`` („Anders einsortieren“)
    "einsortier_wunsch",
    # A4: Foto-Upload, Cover-Ansicht, Befehl 44; das Lesen aus den Tags nur mit ``ffmpeg`` (Skalieren macht Pillow)
    "cover",
    # A9c (13.11., A0-Q): Befehle 47 bis 49, Thema ``warteschlange``; ``als_neu`` bei ``zuordnung/remove``
    "warteschlange",
    "zuordnung_rueckgaengig",
    # A4c (A-2): Audio-Ansicht, Befehle 39 bis 42 (``audio/bereit``, ``hoerstelle/*``), Sortierung ``angehoert``. ``hoerkopie`` fehlt bis A-3
    "reinhoeren",
    # B3 (Stufe B): Befehle 55 und 56, Filter und Feld ``favorit``, Thema ``favoriten``. ``gehoert`` kommt dynamisch dazu (``Hub.faehigkeiten``), nur mit offener Datenbank
    "favoriten",
    # OS3 (18.11., Vertrag W, 14.1): Befehle 57 bis 64, Thema ``online``, Vorschau-HTTP, Filter ``online_vorschlag``. Nicht vom Netz abhängig
    "online_suche",
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
    "warteschlange",
    # B3 (Stufe B): ``gehoert`` nur mit Fähigkeit ``gehoert``, ``favoriten`` nur mit Fähigkeit ``favoriten`` (Vertrag W, 3.1, Nr. 2)
    "gehoert",
    "favoriten",
    # OS3 (Vertrag W, 4.11): nur für Administratoren
    "online",
)
#: Themen, die nur Administratoren bekommen (Vertrag W, 4.11)
NUR_ADMIN_THEMEN: Final = frozenset({"online"})

# --- Namen reserviert ----------------------------------------------------------
GERAETENAMEN: Final = frozenset(
    {"con", "prn", "aux", "nul"}
    | {f"com{i}" for i in range(1, 10)}
    | {f"lpt{i}" for i in range(1, 10)}
    | {f"com{c}" for c in "\u00b9\u00b2\u00b3"}  # COM¹ bis COM³ (Windows reserviert auch die hochgestellten Ziffern)
    | {f"lpt{c}" for c in "\u00b9\u00b2\u00b3"}
)

# --- Testpanel und Audio-Ansicht (Paket A0b, Vertrag W 14.5 und 14.10) ----------
#: Schalter f\u00fcr das Testpanel unter ``/tobibox-test`` (Messungen A0b). Auf ``False`` setzen, um es zu entfernen.
TESTPANEL: Final = True
AUDIO_VERBINDUNGEN_JE_BENUTZER: Final = 6
#: ``audio/bereit`` je Minute und Benutzer (Vertrag W, 2.4 und 14.10); Administratoren sind wie bei allen Mengen ausgenommen
AUDIO_BEREIT_JE_MINUTE: Final = 6
AUDIO_LINK_GUELTIG_S: Final = 86400

# --- Reinhören: Hörstelle und Dauer (Vertrag W, 14.6, 14.7 und 14.10) ---------------------------------
#: ``hoerstelle/set`` je Minute und Benutzer (eigener Zähler)
#: (seit 16.11. 60 statt 30, weil ``spielt`` die Seite öfter rufen lässt; Vertrag W, 15.3)
HOERSTELLE_SCHREIBEN_JE_MINUTE: Final = 60
#: im Speicher sofort, auf der Platte gesammelt (``Store.async_delay_save``)
HOERSTELLE_SPEICHER_VERZOEGERUNG_S: Final = 60
HOERSTELLE_MAX_SERIEN: Final = 2000
HOERSTELLE_MAX_FOLGEN: Final = 100
#: Ist die Dauer einer Folge nicht bekannt, gilt die gesendete bis höchstens so viel
HOERSTELLE_DAUER_UNBEKANNT_MAX_S: Final = 86400
#: „fertig“: bis auf so viele Sekunden ans Ende (Design 5.12)
HOERSTELLE_FERTIG_REST_S: Final = 2
HOERSTELLE_LISTE_LIMIT_MAX: Final = 12
HOERSTELLE_LISTE_LIMIT_VORGABE: Final = 8
#: keine gespeicherte Dauer über 48 Stunden (eine FLAC-Datei mit Stille kann Hunderte Stunden „dauern“)
DAUER_DECKEL_S: Final = 172800
#: feste Zeitgrenze je Datei beim Nachholen im Hintergrund (zusätzlich ``FFPROBE_ZEITLIMIT_S``)
MEDIENINFO_ZEITGRENZE_S: Final = 20
#: Stand der abgeleiteten Werte je Folge im Store ``tobibox.medieninfo`` (Feld ``info_v``): 1 = Dauer (A-2), 2 = dazu Kapitel und Codecs (A-3), 3 = Kapiteltitel roh
#: gespeichert, bereinigt wird erst beim Ausgeben (AM22).
#: Ein Eintrag mit kleinerem Stand wird im Hintergrund noch einmal gemessen (Vertrag W, 14.7).
MEDIENINFO_VERSION: Final = 3
#: Kapitel einer Folge (Vertrag W, 14.7 und 14.10)
KAPITEL_MAX: Final = 500
KAPITEL_TITEL_MAX: Final = 120
#: Rohtitel im Store (vor dem Bereinigen beim Ausgeben, AM22); die Ausgabe kürzt auf ``KAPITEL_TITEL_MAX``
KAPITEL_ROH_MAX: Final = 400

# --- Hörkopie (Vertrag W, 14.8 und 14.10; Werte vorläufig bis zur Messung A0b) ---------------------------------
HOERKOPIE_KBIT: Final = 96
#: feste Zeitgrenze je Datei (nicht aus der Dauer im Dateikopf gerechnet)
HOERKOPIE_ZEITGRENZE_S: Final = 5400
#: ``-t``: Ausgabe höchstens Dauer + Zugabe
HOERKOPIE_T_ZUGABE_S: Final = 5
#: ``-fs``: Ausgabe höchstens Dauer × 12 KB/s × 1,2 (96 kbit/s = 12 000 Byte/s) plus ein fester Sockel für den Behälter (``moov``, ``ftyp``)
HOERKOPIE_BYTES_JE_S: Final = HOERKOPIE_KBIT * 125
HOERKOPIE_FS_FAKTOR: Final = 1.2
HOERKOPIE_FS_SOCKEL_BYTES: Final = 64 * 1024
#: Plausibilität: würde die Kopie (Dauer × 12 KB/s) mehr als so viel mal größer als die Quelle, ist die Dauer verdächtig (Stille in FLAC)
HOERKOPIE_PLAUSIBEL_FAKTOR: Final = 50
HOERKOPIE_SCHLANGE_DATEIEN: Final = 20
HOERKOPIE_SCHLANGE_BYTES: Final = 50 * 1000**3
HOERKOPIE_KONTINGENT_BYTES: Final = 100 * 1000**3
HOERKOPIE_VORZIEHEN_JE_BENUTZER: Final = 1
HOERKOPIE_PARALLEL: Final = 1
#: Speichergrenze (``RLIMIT_AS``) für ``ffmpeg`` (Kodieren braucht mehr als ``ffprobe``; wie das Testpanel)
HOERKOPIE_SPEICHER_BYTES: Final = 2 * 1024**3
#: ``nice`` für ``ffmpeg``
HOERKOPIE_NICE: Final = 10
#: Schätzung der Wartezeit: so viel mal schneller als Echtzeit kodiert ``ffmpeg`` höchstens (Vertrag W, 14.10: 15 bis 30 mal; hier der vorsichtige Wert)
HOERKOPIE_SCHAETZ_FAKTOR: Final = 15
#: Länge einer Datei in der Schätzung, solange ihre Dauer unbekannt ist
HOERKOPIE_SCHAETZ_UNBEKANNT_S: Final = 600
#: Mess-Endpunkt: z\u00e4hlt Bytes und verwirft sie (Grenze wie die k\u00fcnftige Dateigr\u00f6\u00dfe, 2 GiB)
MESS_UPLOAD_MAX_BYTES: Final = 2 * 1024**3
#: ffmpeg-Messung: L\u00e4nge des umgewandelten St\u00fccks und feste Zeitgrenzen
MESS_FFMPEG_AUDIO_S: Final = 600
MESS_FFMPEG_ZEITGRENZE_S: Final = 900
MESS_FFMPEG_KURZ_ZEITGRENZE_S: Final = 20


# --- Stufe B „Gehört“ (Vertrag W, 15.4; Design ``docs/designs/gehoert.md``) -------------------------------
#: Pause innerhalb einer Sitzung und eines Mals (30 Minuten)
GEHOERT_PAUSE_MAX_S: Final = 1800
#: Hörzeit, ab der ein Mal zählt
GEHOERT_MAL_MIN_S: Final = 10
#: „fertig“: Anteil der Folgendauer (Prozent); ohne bekannte Dauer mindestens ``GEHOERT_FERTIG_OHNE_DAUER_S``
GEHOERT_FERTIG_PROZENT: Final = 80
GEHOERT_FERTIG_OHNE_DAUER_S: Final = 60
#: ein ungefähres Datum der Box gilt nur nach dem 1.1.2026 (UTC-Sekunden)
GEHOERT_DATUM_FRUEHESTENS: Final = 1767225600
#: höchstens so viele Sitzungen je Nachricht ``gespielt`` und UUIDs je Quittung (``mqtt-v1.md``, 3.4 und 3.7)
GEHOERT_SITZUNGEN_JE_NACHRICHT: Final = 20
GEHOERT_QUITTUNG_MAX: Final = 100
#: Die Quittung läuft nachlaufend: höchstens so lange nach der ersten wartenden Zeile (Sekunden)
GEHOERT_QUITTUNG_VERZOEGERUNG_S: Final = 2
GEHOERT_QUITTUNG_TTL_S: Final = 3600
#: Aufräumen der Zwischenstände ohne Abschluss: Intervall (Sekunden)
GEHOERT_AUFRAEUMEN_S: Final = 600
REINHOEREN_SPIELER_MAX: Final = 5
#: offene Reinhör-Sitzungen als ``teilweise`` schreiben
REINHOEREN_SCHREIBEN_S: Final = 300
#: Reinhören ohne Fortschritt (und nach einem Neustart von HA) wird nach so langer Zeit ``pause`` bzw. ``verwaist``
REINHOEREN_VERWAIST_S: Final = 1800
#: Zwischenstand einer Box ohne Abschluss wird nach so langer Zeit ``verwaist``
BOX_VERWAIST_S: Final = 86400
#: Takt der Aufräumschleife für Reinhören (Sekunden)
REINHOEREN_TAKT_S: Final = 60
FAVORITEN_MAX: Final = 1000
#: Favoriten im Speicher sofort, auf der Platte gesammelt (Sekunden)
FAVORITEN_SPEICHER_VERZOEGERUNG_S: Final = 5

# --- Stufe B, Paket B3: Befehle 50 bis 56 (Vertrag W, 15.4) ----------------------------------------------------
#: Zeilen einer Zeitreihe in Befehl 50 (darüber ``invalid_format``)
GEHOERT_ZEILEN_MAX: Final = 400
GEHOERT_LIMIT_VORGABE: Final = 50
GEHOERT_LIMIT_MAX: Final = 200
#: ``von`` bis ``bis`` höchstens so viele Jahre (Befehl 50)
GEHOERT_SPANNE_MAX_JAHRE: Final = 3
#: Befehl 51: Vorgabe und Höchstzahl der Einträge
GEHOERT_ZULETZT_LIMIT_VORGABE: Final = 10
GEHOERT_ZULETZT_LIMIT_MAX: Final = 20
#: ``gehoert``/``geaendert`` höchstens alle so viele Sekunden (Vertrag W, 4.9)
GEHOERT_EREIGNIS_BUENDEL_S: Final = 5
#: signierter Pfad des Exports (Befehl 53): Gültigkeit in Sekunden
GEHOERT_EXPORT_LINK_S: Final = 600
#: „Meist gehört“ und der Zwischenspeicher: so viele Kalendertage zurück (Vertrag W, 14.2)
GEHOERT_MEIST_TAGE: Final = 365
#: Befehl 52: Spanne von ``von`` bis ``bis`` in Tagen, Einträge je Liste
TECHNIK_SPANNE_MAX_TAGE: Final = 400
TECHNIK_LISTE_MAX: Final = 2000
#: Befehl 52: höchstens so viele Tabellenzeilen werden gelesen. Der Vertrag kürzt jede der sechs Listen bei ``TECHNIK_LISTE_MAX`` (2000) Einträgen; ein
#: Ladevorgang oder eine Laufzeit braucht zwei Zeilen, also genügen für alle Listen zusammen höchstens rund 12 000 Zeilen. 50 000 lassen reichlich Luft
#: (auch für eine Flut einer einzigen Art) und halten Speicher und Rechenzeit klein; wird die Grenze erreicht, steht ``weitere`` auf ``true``.
TECHNIK_ZEILEN_MAX: Final = 50_000
#: ``favorit/set`` je Minute und Benutzer (eigener Zähler; Administratoren ausgenommen, 2.4)
FAVORITEN_JE_MINUTE: Final = 30


# --- Online-Suche (Vertrag W, 3.15 „Grenzen“; Design ``docs/designs/online-suche.md``) ---------------------------
ONLINE_TREFFER_MAX: Final = 10
#: so viele der obersten Treffer laden ihr Bild schon beim Suchen (Vorschau); bei den übrigen holt Befehl 58 es nach
ONLINE_TREFFER_BILDER: Final = 5
#: Kantenlänge der Vorschau (``GET /api/tobibox/online/vorschau/<treffer_id>``)
ONLINE_VORSCHAU_PX: Final = COVER_KLEIN_PX
ONLINE_BESCHREIBUNG_KURZ: Final = 300
ONLINE_BESCHREIBUNG_MAX: Final = 2000
ONLINE_UEBERSPRUNGEN_MAX: Final = 50
ONLINE_AENDERUNGEN_TAGE: Final = 30
ONLINE_MARKE_KEINER_TAGE: Final = 30
ONLINE_MARKE_FEHLER_TAGE: Final = 1
ONLINE_AENDERUNGEN_MAX: Final = 20
ONLINE_VERWORFEN_MAX: Final = 200
ONLINE_STAND_BUENDEL_S: Final = 2.0
