"""Fehlercodes des Vertrags W (Abschnitt 7) als Ausnahme."""

from __future__ import annotations

from typing import Final

#: HTTP-Status je Code (Vertrag W, Abschnitt 7)
HTTP_STATUS: Final = {
    "invalid_format": 400,
    "unauthorized": 401,
    "unknown_error": 500,
    "anfrage_id_konflikt": 409,
    "medien_nicht_erreichbar": 503,
    "medien_schreibfehler": 500,
    "kein_speicher": 507,
    "mqtt_nicht_verbunden": 503,
    "serie_nicht_gefunden": 404,
    "folge_nicht_gefunden": 404,
    "eintrag_nicht_gefunden": 404,
    "export_nicht_gefunden": 404,
    "export_ungueltig": 422,
    "box_unbekannt": 404,
    "box_offline": 409,
    "kennung_ungueltig": 400,
    "ziel_ungueltig": 400,
    "zuordnung_existiert": 409,
    "zuordnung_geaendert": 409,
    "konfig_zu_gross": 413,
    "konfig_nicht_bereit": 409,
    "name_ungueltig": 400,
    "reihenfolge_ungueltig": 400,
    "stand_veraltet": 409,
    "tobies_betroffen": 409,
    "ueberraschung_existiert": 409,
    "lernmodus_laeuft": 409,
    "kein_lernmodus": 404,
    "rueckfrage_abgelaufen": 409,
    "datei_existiert": 409,
    "serie_existiert": 409,
    "upload_laeuft": 409,
    "zu_viele_uploads": 429,
    "datei_zu_gross": 413,
    "format_nicht_erlaubt": 415,
    "keine_version": 404,
    "einstellung_ungueltig": 400,
    "sortierung_laeuft": 409,
    "zu_viele_aenderungen": 429,
    "wunsch_ungueltig": 400,
}


class TobiboxFehler(Exception):
    """Ein Fehler mit Code aus Abschnitt 7 des Vertrags W.

    ``details`` ergänzt den Klartext (Platzhalter in ``strings.json``), z. B. ``{"geloescht": 3}``.
    """

    def __init__(self, code: str, **details: object) -> None:
        super().__init__(code)
        self.code = code
        self.details = details

    @property
    def http_status(self) -> int:
        return HTTP_STATUS.get(self.code, 500)
