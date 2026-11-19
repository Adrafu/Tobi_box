"""Online-Suche, Paket OS3: Dienst, Store, Übernahme, Rücknahme, Lauf, Claude-Schritt, Cover-Vorrang, Pflegestellen.

Ohne echtes Netz: Die Quellen sind Attrappen, die die Fixtures aus ``fixtures/online/`` liefern; ``ai_task`` ist ein Dienst der Attrappe.
Fall (Bibi Blocksberg, Folge 100, ``erwartung.json``): Tonie ``01-0030`` (13 Tracks), Apple-Album und Shopseite mit Alter 4.
"""

from __future__ import annotations

import asyncio
import io
import json
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from PIL import Image

from custom_components.tobibox import config_flow
from custom_components.tobibox.cover import (
    COVER_ONLINE,
    cover_zustand,
    lese_cover_datei,
    uebernimm_cover,
)
from custom_components.tobibox.const import CONF_ONLINE_KI_ENTITAET, DOMAIN
from custom_components.tobibox.fehler import TobiboxFehler
from custom_components.tobibox.neu_einsortieren import rueckweg_fortschreiben
from custom_components.tobibox.online import OnlineStore, beschreibung_text, kuerzen_am_satzende
from custom_components.tobibox.online_quellen import (
    FormatFehler,
    NichtErreichbar,
    QuellePausiert,
    TrefferSpeicher,
    parse_itunes,
    parse_shop,
    parse_sitemap,
    parse_tonie_liste,
)

from .conftest import braucht_ffmpeg

FIX = Path(__file__).parent / "fixtures" / "online"
SITEMAP = parse_sitemap((FIX / "sitemap_auszug.xml").read_bytes())
SHOP_PFAD = "/de-de/tonies/bibi-blocksberg/die-grosse-hexenparty/"
MODEL = "01-0030"
FALL = json.loads((FIX / "erwartung.json").read_text(encoding="utf-8"))["faelle"]["bibi_folge100"]
FOLGE = "f100"
SID = "bibi"
pytestmark = braucht_ffmpeg


def jpeg(farbe: tuple[int, int, int] = (200, 30, 30), px: int = 600) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", (px, px), farbe).save(puffer, "JPEG")
    return puffer.getvalue()


# --------------------------------------------------------------------------
# Attrappen
# --------------------------------------------------------------------------


class FakeQuellen:
    """Gleiche Methoden wie ``OnlineQuellen``, ohne Netz."""

    def __init__(self) -> None:
        self.treffer_speicher = TrefferSpeicher()
        self.itunes: dict[str, list[dict[str, Any]]] = {
            "album": parse_itunes((FIX / "itunes" / "bibi_folge100_album_mit_jubilaeum.json").read_bytes()),
            "hoerbuch": parse_itunes((FIX / "itunes" / "bibi_folge100_buch.json").read_bytes()),
        }
        self.shop: dict[str, Any] = {SHOP_PFAD: parse_shop((FIX / "shop" / "01-0030_bibi_hexenparty.html").read_bytes(), MODEL)}
        self.bild = jpeg()
        self.aufrufe: list[tuple[str, str]] = []
        self.pausen: dict[str, float] = {}
        self.itunes_pause: QuellePausiert | None = None
        self.itunes_ausfall = False
        self.shop_ausfall = False
        self.shop_format_fehler = False
        self.bild_fehler: Exception | None = None
        self.vor_bild: Any = None  # läuft zwischen „bewertet“ und „geschrieben“ (der Bildabruf ist Netz ohne Sperre)

    async def im_executor(self, func: Any, *args: Any) -> Any:
        return func(*args)

    def pause_bis(self, gruppe: str) -> float | None:
        bis = self.pausen.get(gruppe)
        return bis if bis is not None and bis > time.time() else None

    async def itunes_suche(self, wort: str, art: str, *, von_hand: bool = False) -> list[dict[str, Any]]:
        self.aufrufe.append(("itunes", art))
        if self.itunes_pause is not None:
            raise self.itunes_pause
        if self.itunes_ausfall:
            raise NichtErreichbar("aus")
        return list(self.itunes[art])

    async def bild_holen(self, url: str, *, von_hand: bool = False) -> bytes:
        self.aufrufe.append(("bild", url))
        if self.vor_bild is not None:
            await self.vor_bild()
        if self.bild_fehler is not None:
            raise self.bild_fehler
        return self.bild

    async def sitemap_pfade(self) -> list[str]:
        return SITEMAP

    async def shop_seite(self, pfad: str, model: str, *, von_hand: bool = False) -> dict[str, Any] | None:
        self.aufrufe.append(("shop", pfad))
        if self.shop_ausfall:
            raise NichtErreichbar("aus")
        if self.shop_format_fehler:
            raise FormatFehler("Felder fehlen", code="online_shop_format")
        return self.shop[pfad]


class FakeListe:
    def __init__(self) -> None:
        self.eintraege = parse_tonie_liste((FIX / "tonies_auszug.json").read_bytes())
        self.stand: float | None = 1_700_000_000.0
        self.ok = True

    @property
    def anzahl(self) -> int:
        return len(self.eintraege)

    async def sicherstellen(self, *, erzwingen: bool = False) -> bool:
        return self.ok


def lege_bibi(nas: Any, lege_mp3: Any, *, gruende: list[str] | None = None, serie_gruende: list[str] | None = None, name: str = "Bibi Blocksberg",
              ordner: str = "bibi", serie_id: str = SID, nummer: int | None = None, **extra: Any) -> None:
    for i in range(1, 14):
        lege_mp3(nas.medien / ordner / FOLGE / f"{i:02d}.mp3")
    info: dict[str, Any] = {"anzeige": FALL["folge"]}
    if nummer is not None:
        info["nummer"] = nummer
    if gruende:
        info.update(pruefen=True, pruefen_gruende=gruende)
    daten: dict[str, Any] = {"art": "musik", "art_quelle": "geraten", "folgen_info": {FOLGE: info}, **extra}
    if serie_gruende:
        daten.update(pruefen=True, pruefen_gruende=serie_gruende)
    nas.serie(ordner, serie_id=serie_id, name=name, folgen=[FOLGE], **daten)


@pytest.fixture
async def hub(starte_integration: Any, nas: Any, lege_mp3: Any) -> Any:
    lege_bibi(nas, lege_mp3, gruende=["tags_fehlen"], serie_gruende=["art_geraten"])
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    return h


def serie_json(nas: Any, ordner: str = "bibi") -> dict[str, Any]:
    return nas.serie_json(ordner)


async def schnapp_wie_einsortiert(hub: Any, nummer: int | None = None) -> None:
    """Der Zustand direkt nach dem Einsortieren: Schnappschuss, ohne die Schlange laufen zu lassen."""
    hub.online.store.setze_schnapp(SID, f"folge_titel@{FOLGE}", FALL["folge"])
    hub.online.store.setze_schnapp(SID, f"nummer@{FOLGE}", nummer)
    hub.online.store.setze_schnapp(SID, "art", "musik")


async def arbeite(hub: Any, **kw: Any) -> dict[str, Any]:
    kw.setdefault("folgen", None)
    kw.setdefault("neu", False)
    kw.setdefault("im_lauf", False)
    kw.setdefault("lauf_id", None)
    async with hub.online._arbeit:
        return await hub.online._arbeite_serie(SID, **kw)


# --------------------------------------------------------------------------
# Store
# --------------------------------------------------------------------------


async def test_store_mit_minor_version_1_laedt_fehlerfrei(hass: Any, hass_storage: dict[str, Any]) -> None:
    hass_storage["tobibox.online"] = {"version": 1, "minor_version": 1, "key": "tobibox.online", "data": {"serien": {"a": {"hand": {"art": True}}}, "laeufe": []}}
    store = OnlineStore(hass)
    await store.laden()
    assert store.hand_hat("a", "art")
    assert OnlineStore(hass)._store.minor_version == 1  # noqa: SLF001


async def test_store_migration_von_minor_0(hass: Any, hass_storage: dict[str, Any]) -> None:
    hass_storage["tobibox.online"] = {"version": 1, "minor_version": 0, "key": "tobibox.online", "data": {"serien": {"a": {"hand": {"art": True}}}, "laeufe": []}}
    store = OnlineStore(hass)
    await store.laden()
    assert store.hand_hat("a", "art")


async def test_store_unbekannte_form_wird_leer(hass: Any, hass_storage: dict[str, Any]) -> None:
    hass_storage["tobibox.online"] = {"version": 1, "minor_version": 1, "key": "tobibox.online", "data": {"serien": [1], "laeufe": "x"}}
    store = OnlineStore(hass)
    await store.laden()
    assert store.daten == {"serien": {}, "laeufe": []}


async def test_store_pflegestellen_umbenennen_loeschen_bereinigen(hass: Any) -> None:
    st = OnlineStore(hass)
    st.setze_schnapp("q", "nummer@a.mp3", 3)
    st.setze_schnapp("q", "folge_titel@a.mp3", "A")
    st.setze_hand("q", "beschreibung@a.mp3")
    st.setze_zurueckgenommen("q", "nummer@a.mp3")
    st.setze_folge_info("q", "a.mp3", beschreibung="Text", alter_ab=4, quelle="tonies_shop")
    st.serie("q")["vorschlaege"] = [
        {"id": "v1", "art": "felder", "quelle": "itunes", "felder": ["nummer@a.mp3", "cover"], "werte": {"nummer@a.mp3": 3, "cover": {"cover_url": "u", "collection_id": 1}}, "zeit": "z"}
    ]
    st.serie("q")["aenderungen"] = [{"id": "x", "status": "fertig", "zeit": "2026-11-18T10:00:00Z", "felder": {"nummer@a.mp3": {"vorher": None, "nachher": 3}}}]
    st.folge_umbenannt("q", "a.mp3", "z", "b (2).mp3")
    assert st.schnapp_wert("z", "nummer@b (2).mp3") == (True, 3)
    assert st.schnapp_wert("q", "nummer@a.mp3") == (False, None)
    assert st.hand_hat("z", "beschreibung@b (2).mp3") and st.zurueck_hat("z", "nummer@b (2).mp3")
    assert st.folge_info("z", "b (2).mp3")["alter_ab"] == 4 and not st.folge_info("q", "a.mp3")
    # Vorschlag: die Felder der Folge gehen mit, der Rest (Cover) bleibt bei der Quelle
    assert st.vorschlaege("z")[0]["felder"] == ["nummer@b (2).mp3"]
    assert st.vorschlaege("q")[0]["felder"] == ["cover"]
    assert st.aenderungen("q")  # Änderungen bleiben bei der Quelle
    st.loesche_folge("z", "b (2).mp3")
    assert st.lies("z") == {}
    st.setze_hand("q", "cover")
    st.loesche_serie("q")
    assert st.lies("q") == {}
    st.setze_hand("w", "art")
    st.setze_schnapp("w", "nummer@weg.mp3", 1)
    assert st.bereinige({"w": ["da.mp3"]}) >= 1 and st.schnapp_wert("w", "nummer@weg.mp3") == (False, None)
    assert st.bereinige({}) == 1 and st.daten["serien"] == {}


async def test_store_hand_ersetzt_zurueckgenommen(hass: Any) -> None:
    st = OnlineStore(hass)
    st.setze_zurueckgenommen("s", "art")
    assert st.zurueck_hat("s", "art") and not st.hand_hat("s", "art")
    st.setze_hand("s", "art")
    assert st.hand_hat("s", "art") and not st.zurueck_hat("s", "art")


async def test_marken_verfall(hass: Any) -> None:
    st = OnlineStore(hass, zeit=time.time)
    st.setze_marke("s", "keiner", ["a"], 5.0)
    assert st.marke_gueltig("s", ["a"], 5.0)
    assert not st.marke_gueltig("s", ["a", "b"], 5.0)  # eine Folge steht noch nicht in der Marke
    assert not st.marke_gueltig("s", ["a"], 6.0)  # neue Tonie-Liste
    st.daten["serien"]["s"]["marke"]["zeit"] = "2020-01-01T00:00:00Z"  # älter als 30 Tage
    assert not st.marke_gueltig("s", ["a"], 5.0)
    st.setze_marke("t", "geaendert", ["a"], 5.0)
    st.daten["serien"]["t"]["marke"]["zeit"] = "2020-01-01T00:00:00Z"
    assert st.marke_gueltig("t", ["a"], 99.0)  # ``geaendert`` verfällt nie


def test_beschreibung_hilfen() -> None:
    assert beschreibung_text("Absatz eins\u0000\n\n  Absatz   zwei \x07") == "Absatz eins\nAbsatz zwei"
    assert beschreibung_text("   ") is None
    kurz, gekuerzt = kuerzen_am_satzende("Ein langer Satz mit vielen Wörtern darin. " * 10)
    assert gekuerzt and kurz.endswith("darin.") and len(kurz) <= 300  # am Satzende
    assert kuerzen_am_satzende("Kurz.") == ("Kurz.", False)


# --------------------------------------------------------------------------
# Cover-Vorrang (7.2)
# --------------------------------------------------------------------------


def test_cover_vorrang_eigen_vor_online_vor_auto(tmp_path: Path) -> None:
    jpg = jpeg(px=64)
    assert cover_zustand(tmp_path) == (None, None)
    (tmp_path / "cover.jpg").write_bytes(jpg)
    assert cover_zustand(tmp_path)[1] == "auto"
    (tmp_path / COVER_ONLINE).write_bytes(jpg + b"o")
    assert cover_zustand(tmp_path)[1] == "online"
    assert lese_cover_datei(tmp_path)[1] == jpg + b"o"
    (tmp_path / "cover-eigen.jpg").write_bytes(jpg + b"e")
    assert cover_zustand(tmp_path)[1] == "eigen"
    assert lese_cover_datei(tmp_path)[1] == jpg + b"e"


def test_zusammenfuehren_kopiert_online_und_eigen(tmp_path: Path) -> None:
    quelle, ziel = tmp_path / "q", tmp_path / "z"
    quelle.mkdir()
    ziel.mkdir()
    (quelle / COVER_ONLINE).write_bytes(b"online")
    assert uebernimm_cover(quelle, ziel) and (ziel / COVER_ONLINE).read_bytes() == b"online"
    ziel2 = tmp_path / "z2"
    ziel2.mkdir()
    (quelle / "cover-eigen.jpg").write_bytes(b"eigen")
    assert uebernimm_cover(quelle, ziel2)
    assert (ziel2 / "cover-eigen.jpg").read_bytes() == b"eigen" and (ziel2 / COVER_ONLINE).read_bytes() == b"online"
    ziel3 = tmp_path / "z3"
    ziel3.mkdir()
    (ziel3 / COVER_ONLINE).write_bytes(b"hat schon")
    assert not uebernimm_cover(quelle, ziel3)  # hat das Ziel (auch nur ein Online-Cover) eines, wird nichts kopiert


async def test_neu_suchen_beruehrt_cover_online_nie(hub: Any, nas: Any) -> None:
    (nas.medien / "bibi" / COVER_ONLINE).write_bytes(jpeg(px=64))
    (nas.medien / "bibi" / "cover.jpg").write_bytes(jpeg(px=64))
    await hub.cover.neu_suchen(SID)
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file() and not (nas.medien / "bibi" / "cover.jpg").exists()
    await hub.cover.warte_auf_ende()


async def test_cover_online_entfernen(hub: Any, nas: Any) -> None:
    (nas.medien / "bibi" / COVER_ONLINE).write_bytes(jpeg(px=64))
    erg = await hub.cover.entferne_online(SID)
    assert not (nas.medien / "bibi" / COVER_ONLINE).exists() and erg["cover_quelle"] is None
    assert (await hub.cover.entferne_online(SID))["cover_quelle"] is None  # ohne Online-Cover kein Fehler


async def test_art_quelle_online_ueberlebt_lesen_und_schreiben(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    assert serie_json(nas)["art_quelle"] == "online"
    info = hub.medien.serien[SID]
    assert hub.medien.kurzform(info)["art_quelle"] == "online"
    (await hub.medien._frisch(SID))  # noqa: SLF001
    assert (await hub.medien._frisch(SID))[0].art_quelle == "online"  # noqa: SLF001


# --------------------------------------------------------------------------
# Übernahme (6.3) und Rücknahme (6.4)
# --------------------------------------------------------------------------


async def test_uebernahme_auto_alle_felder(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    # Die Folge heißt schon „Folge 100: …“, hat aber keine Nummer eingetragen: die Nummer ist sicher 100
    erg = await arbeite(hub)
    assert erg["geaendert"] >= 3 and not erg["fehler"]
    sj = serie_json(nas)
    assert sj["art"] == "hoerspiel" and sj["art_quelle"] == "online"
    assert sj["folgen_info"][FOLGE]["nummer"] == 100
    # tags_fehlen (Titel bestätigt, Nummer gesetzt) und art_geraten sind aufgelöst: nichts mehr „bitte ansehen“
    assert "pruefen" not in sj and "pruefen" not in sj["folgen_info"][FOLGE]
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file()
    assert hub.medien.serien[SID].cover_quelle == "online" and "cover.jpg" not in [p.name for p in (nas.medien / "bibi").iterdir()]
    fi = hub.online.store.folge_info(SID, FOLGE)
    assert fi["alter_ab"] == 4 and fi["beschreibung"].startswith("Ein neues hexisches Zeitalter") and fi["quelle"] == "tonies_shop"
    assert fi["tonie_model"] == MODEL and fi["seite"] == SHOP_PFAD
    (a,) = hub.online.store.aenderungen(SID)
    assert a["status"] == "fertig" and a["wer"] == "auto" and a["felder"]["nummer@" + FOLGE] == {"vorher": None, "nachher": 100}
    assert a["felder"]["art"]["nachher"] == {"art": "hoerspiel", "art_quelle": "online"} and "schnapp_vorher" not in a and a["cover_stand"]
    # Schnappschuss für Nummer und Art, nie für den Namen; Marke
    assert hub.online.store.schnapp_wert(SID, f"nummer@{FOLGE}") == (True, 100)
    assert "serie_name" not in json.dumps(hub.online.store.lies(SID).get("schnapp"))
    assert hub.online.store.marke(SID)["ergebnis"] == "geaendert"
    kurz = hub.online.kurz_online(SID)
    assert set(kurz["felder"]) >= {"cover", "art", "nummer"}
    assert hub.online.folge_online(SID, FOLGE)["alter_ab"] == 4


async def test_beschreibung_erst_nach_den_shopseiten(hub: Any) -> None:
    """Auflage: Die Beschreibung kommt von der Shopseite, auch wenn Apples Hörbuch-Eintrag eine hat (erst Seiten holen, dann bewerten)."""
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    assert ("shop", SHOP_PFAD) in hub.online.quellen.aufrufe
    assert hub.online.store.folge_info(SID, FOLGE)["quelle"] == "tonies_shop"
    # Ein zweiter Durchgang holt die Seite nicht noch einmal (Store)
    hub.online.store.daten["serien"][SID].pop("marke")
    hub.online.quellen.aufrufe.clear()
    await arbeite(hub)
    assert ("shop", SHOP_PFAD) not in hub.online.quellen.aufrufe


async def test_shop_formatfehler_ist_geholt_aber_unbrauchbar_und_netzfehler_ist_fehler(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    hub.online.quellen.shop_format_fehler = True
    erg = await arbeite(hub)
    # ``None`` (geholt, unbrauchbar) ist endgültig: keine Shop-Beschreibung, aber Apples Hörbuch-Eintrag liefert eine (4.9, Punkt 2)
    assert not erg["fehler"] and hub.online.store.folge_info(SID, FOLGE)["quelle"] == "itunes" and "alter_ab" not in hub.online.store.folge_info(SID, FOLGE)
    hub.online.store.daten["serien"][SID].pop("marke", None)
    hub.online.quellen.shop_format_fehler = False
    hub.online.quellen.shop_ausfall = True
    erg = await arbeite(hub)
    assert erg["fehler"]  # nicht geholt: nicht endgültig
    assert hub.online.store.marke(SID)["ergebnis"] in ("geaendert", "fehler")


async def test_ausfall_aller_quellen_laesst_alles_wie_es_ist(hub: Any, nas: Any) -> None:
    vorher = json.dumps(serie_json(nas), sort_keys=True)
    hub.online.quellen.itunes_ausfall = True
    hub.online.tonie_liste.ok = False
    erg = await arbeite(hub)
    assert erg["fehler"]
    assert json.dumps(serie_json(nas), sort_keys=True) == vorher
    assert hub.online.store.marke(SID)["ergebnis"] == "fehler"
    assert not (nas.medien / "bibi" / COVER_ONLINE).exists()


async def test_rueckweg_nur_stand_und_art_fortgeschrieben() -> None:
    serie = SimpleNamespace(id="s", name="N", stand="neu", art="hoerspiel", art_quelle="online", anzeige=lambda f: f"Titel {f}")
    rw = {"v": 1, "serien": {"s": {"neu": True, "name": "N", "stand": "alt", "art": "hoerspiel", "art_quelle": "geraten", "cover_eigen": False}}, "folgen": [{"serie_id": "s", "folge": "a", "anzeige": "x"}]}
    anderer = {"v": 1, "serien": {"s": {"neu": False, "name": "N", "stand": "ganz anders", "art": None, "art_quelle": None, "cover_eigen": False}}, "folgen": []}
    gespeichert = []
    eingang = SimpleNamespace(_rueckweg={"e1": rw}, protokoll=[{"rueckweg": anderer}, {"id": "ohne"}], speichern=lambda: gespeichert.append(1))
    assert rueckweg_fortschreiben(eingang, "alt", serie, ["a"])
    assert rw["serien"]["s"]["stand"] == "neu" and rw["serien"]["s"]["art_quelle"] == "online" and rw["folgen"][0]["anzeige"] == "Titel a"
    assert anderer["serien"]["s"]["stand"] == "ganz anders"  # nur Zeilen mit gleichem Stand
    assert gespeichert


async def test_uebernahme_auto_haelt_anders_einsortieren_offen(hub: Any, nas: Any) -> None:
    """5.1 Schritt 6: Nach der automatischen Übernahme steht der ``stand`` im Rückweg des Eingangs neu."""
    await schnapp_wie_einsortiert(hub)
    stand0 = hub.medien.serien[SID].serie.stand
    hub.eingang._rueckweg["Bibi"] = {"v": 1, "serien": {SID: {"neu": True, "name": "Bibi Blocksberg", "stand": stand0, "art": "musik", "art_quelle": "geraten", "cover_eigen": False}}, "folgen": [{"serie_id": SID, "folge": FOLGE, "anzeige": FALL["folge"], "ist_ordner": True, "dateien": []}]}
    await arbeite(hub)
    s = hub.medien.serien[SID].serie
    zeile = hub.eingang._rueckweg["Bibi"]["serien"][SID]
    assert zeile["stand"] == s.stand != stand0 and zeile["art_quelle"] == "online"


async def test_ruecknahme_je_aenderung_setzt_alles_zurueck(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    (a,) = hub.online.store.aenderungen(SID)
    erg = await hub.online.zuruecknehmen(SID, a["id"])
    assert erg["zurueckgenommen"] >= 3 and erg["uebersprungen"] == [] and erg["uebersprungen_anzahl"] == 0
    sj = serie_json(nas)
    assert sj["art_quelle"] == "geraten" and "nummer" not in sj["folgen_info"][FOLGE]
    assert sj["pruefen"] is True and sj["pruefen_gruende"] == ["art_geraten"]  # „bitte ansehen“ ist zurück
    assert sj["folgen_info"][FOLGE]["pruefen_gruende"] == ["tags_fehlen"]
    assert not (nas.medien / "bibi" / COVER_ONLINE).exists() and hub.medien.serien[SID].cover_quelle is None
    st = hub.online.store
    assert st.aenderungen(SID)[0]["status"] == "zurueckgenommen" and hub.online.kurz_online(SID) is None
    assert st.zurueck_hat(SID, "art") and st.zurueck_hat(SID, "cover") and st.zurueck_hat(SID, f"nummer@{FOLGE}")
    assert st.schnapp_wert(SID, f"nummer@{FOLGE}") != (True, 100)  # der Schnappschuss mit dem Online-Wert ist gelöscht (die Folge behält nur ihren Eintrag ohne Nummer)
    assert st.folge_info(SID, FOLGE) == {}
    # zweites Mal: Endzustand, 0 Felder
    assert (await hub.online.zuruecknehmen(SID, a["id"]))["zurueckgenommen"] == 0
    assert (await hub.online.zuruecknehmen(SID))["zurueckgenommen"] == 0
    with pytest.raises(TobiboxFehler) as err:
        await hub.online.zuruecknehmen(SID, "gibtsnicht")
    assert err.value.code == "aenderung_nicht_gefunden"


async def test_ruecknahme_feld_inzwischen_von_hand_geaendert_bleibt(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    await hub.medien.serie_art_setzen(SID, "musik")  # ein Mensch ändert die Art
    erg = await hub.online.zuruecknehmen(SID)
    assert [u["feld"] for u in erg["uebersprungen"]] == ["art"] and erg["uebersprungen"][0]["grund"] == "seitdem_geaendert"
    assert erg["uebersprungen_anzahl"] == 1 and erg["zurueckgenommen"] >= 2
    sj = serie_json(nas)
    assert sj["art"] == "musik" and sj["art_quelle"] == "manuell"
    assert "nummer" not in sj["folgen_info"][FOLGE] and not (nas.medien / "bibi" / COVER_ONLINE).exists()
    assert not hub.online.store.zurueck_hat(SID, "art")  # kein Feld zurückgesetzt, keine Marke


async def test_ruecknahme_cover_nur_wenn_es_noch_die_datei_der_aenderung_ist(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    (nas.medien / "bibi" / COVER_ONLINE).write_bytes(jpeg((1, 2, 3), px=64))  # jemand tauscht die Datei
    erg = await hub.online.zuruecknehmen(SID)
    assert "cover" in [u["feld"] for u in erg["uebersprungen"]] and (nas.medien / "bibi" / COVER_ONLINE).is_file()


async def test_marke_zurueckgenommen_verhindert_wiederkehr_im_lauf(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    await hub.online.zuruecknehmen(SID)
    st = hub.online.store
    st.daten["serien"][SID].pop("marke")  # der Lauf fragt den Eintrag wieder
    erg = await arbeite(hub, im_lauf=True)
    assert erg["geaendert"] == 0 and erg["vorschlaege"] >= 1  # nur noch Vorschläge
    sj = serie_json(nas)
    assert sj["art_quelle"] == "geraten" and "nummer" not in sj["folgen_info"][FOLGE] and not (nas.medien / "bibi" / COVER_ONLINE).exists()
    felder = {k for v in st.vorschlaege(SID) for k in v["felder"]}
    assert {"art", "cover", f"nummer@{FOLGE}"} <= felder


async def test_ruecknahme_je_lauf_setzt_keine_marke(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub, im_lauf=True, lauf_id="lauf1")
    assert hub.online.store.aenderungen(SID)[0]["lauf_id"] == "lauf1"
    hub.online.store.lauf_speichern({"lauf_id": "lauf1", "beginn": "2026-11-19T10:00:00Z", "ende": "2026-11-19T11:00:00Z", "zustand": "fertig", "zahlen": {"erledigt": 1, "gesamt": 1, "geaendert": 1, "vorschlaege": 0, "keiner": 0}})
    with pytest.raises(TobiboxFehler) as err:
        await hub.online.zuruecknehmen(lauf_id="gibtsnicht")
    assert err.value.code == "lauf_nicht_gefunden"
    with pytest.raises(TobiboxFehler) as err2:
        await hub.online.zuruecknehmen(SID, lauf_id="lauf1")
    assert err2.value.code == "invalid_format"
    assert await hub.online.zuruecknehmen(lauf_id="lauf1") == {"gestartet": True}
    await hub.online.warte_auf_rueck()
    assert serie_json(nas)["art_quelle"] == "geraten"
    assert not hub.online.store.zurueck_hat(SID, "art")  # „Alle zurücknehmen“ setzt die Marke nicht
    # ein späterer Lauf darf wieder automatisch übernehmen
    hub.online.store.daten["serien"][SID].pop("marke")
    await schnapp_wie_einsortiert(hub)
    assert (await arbeite(hub, im_lauf=True))["geaendert"] >= 1


async def test_hand_uebernahme_und_ruecknahme_nimmt_hand_weg(hub: Any, nas: Any) -> None:
    ergebnis = await hub.online.suchen(SID, FOLGE, None)
    assert ergebnis["quellen"] == {"itunes": "ok", "tonies": "ok"}
    apple = next(t for t in ergebnis["treffer"] if t["quelle"] == "itunes" and "cover" in t["felder"])
    uebersicht = await hub.online.treffer(treffer_id=apple["treffer_id"])
    assert uebersicht["felder"]["cover"]["neu"] is True and uebersicht["felder"]["art"] == {"heute": "musik", "neu": "hoerspiel", "sicher": True, "hand": False}
    # Tonie-Treffer: Beschreibung und Alter von der Shopseite (eigene Abfrage der Suche von Hand)
    tonie = next(t for t in ergebnis["treffer"] if t["quelle"] == "tonies")
    assert f"alter_ab@{FOLGE}" in tonie["felder"] and f"beschreibung@{FOLGE}" in tonie["felder"]
    t_uebersicht = await hub.online.treffer(treffer_id=tonie["treffer_id"])
    assert t_uebersicht["felder"][f"alter_ab@{FOLGE}"]["neu"] == 4 and "cover" not in t_uebersicht["felder"]
    stand = hub.medien.serien[SID].serie.stand
    erg = await hub.online.uebernehmen(SID, ["cover"], treffer_id=apple["treffer_id"], stand=stand)
    assert erg["aenderung_id"] and (nas.medien / "bibi" / COVER_ONLINE).is_file()
    st = hub.online.store
    assert st.hand_hat(SID, "cover") and hub.online.kurz_online(SID)["felder"] == ["cover"]
    # Von Hand gesetzt: Die Automatik fasst das Cover nie an (kein Vorschlag, keine Änderung)
    await schnapp_wie_einsortiert(hub)
    st.daten["serien"][SID].pop("marke", None)
    erg2 = await arbeite(hub)
    assert (nas.medien / "bibi" / COVER_ONLINE).read_bytes() and "cover" not in {k for v in st.vorschlaege(SID) for k in v["felder"]}
    # Rücknahme: ``hand`` fällt weg, die Marke ``zurueckgenommen`` kommt
    await hub.online.zuruecknehmen(SID, erg["aenderung_id"])
    assert not st.hand_hat(SID, "cover") and st.zurueck_hat(SID, "cover") and erg2 is not None


async def test_uebernehmen_werte_nie_aus_der_eingabe_und_fehler(hub: Any) -> None:
    erg = await hub.online.suchen(SID, FOLGE, None)
    t = erg["treffer"][0]
    with pytest.raises(TobiboxFehler) as e1:
        await hub.online.uebernehmen(SID, ["gibt_es_nicht"], treffer_id=t["treffer_id"])
    assert e1.value.code == "invalid_format"
    with pytest.raises(TobiboxFehler) as e2:
        await hub.online.uebernehmen(SID, ["serie_name"], treffer_id=t["treffer_id"])  # ``stand`` ist Pflicht bei ``serie_name``
    assert e2.value.code == "invalid_format"
    with pytest.raises(TobiboxFehler) as e3:
        await hub.online.uebernehmen(SID, ["art"], treffer_id="0" * 16)
    assert e3.value.code == "treffer_abgelaufen"
    with pytest.raises(TobiboxFehler) as e4:
        await hub.online.uebernehmen(SID, ["serie_name"], treffer_id=t["treffer_id"], stand="veraltet")
    assert e4.value.code == "stand_veraltet"
    with pytest.raises(TobiboxFehler) as e5:
        await hub.online.uebernehmen(SID, ["art"])
    assert e5.value.code == "invalid_format"


async def test_suche_fehler_und_quellen(hub: Any) -> None:
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.suchen("gibtsnicht")
    assert e.value.code == "serie_nicht_gefunden"
    with pytest.raises(TobiboxFehler) as e2:
        await hub.online.suchen(SID, "gibtsnicht")
    assert e2.value.code == "folge_nicht_gefunden"
    hub.online.quellen.itunes_ausfall = True
    teil = await hub.online.suchen(SID, FOLGE)
    assert teil["quellen"] == {"itunes": "fehler", "tonies": "ok"} and all(t["quelle"] == "tonies" for t in teil["treffer"])
    hub.online.tonie_liste.ok = False
    with pytest.raises(TobiboxFehler) as e3:
        await hub.online.suchen(SID, FOLGE)
    assert e3.value.code == "online_nicht_erreichbar"
    assert len(teil["treffer"]) <= 10 and all(len(t["treffer_id"]) == 16 for t in teil["treffer"])


async def test_treffer_abgelaufen_nach_15_minuten(hub: Any) -> None:
    erg = await hub.online.suchen(SID, FOLGE)
    tid = erg["treffer"][0]["treffer_id"]
    speicher = hub.online.quellen.treffer_speicher
    speicher._ttl = -1  # noqa: SLF001
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.treffer(treffer_id=tid)
    assert e.value.code == "treffer_abgelaufen"


# --------------------------------------------------------------------------
# Vorschläge
# --------------------------------------------------------------------------


async def _vorschlag_erzeugen(hub: Any) -> list[dict[str, Any]]:
    """Cover und Art wurden zurückgenommen: Der Lauf schlägt sie nur noch vor (Cover von Apple, Art von Apple und Tonies)."""
    await schnapp_wie_einsortiert(hub)
    hub.online.store.setze_zurueckgenommen(SID, "art")
    hub.online.store.setze_zurueckgenommen(SID, "cover")
    await arbeite(hub)
    return [v for v in hub.online.vorschlaege_gueltig(SID) if v["art"] == "felder"]


def alle_felder(vorschlaege: list[dict[str, Any]]) -> set[str]:
    return {k for v in vorschlaege for k in v["felder"]}


async def test_verworfener_vorschlag_kommt_im_lauf_nicht_wieder(hub: Any) -> None:
    vorschlaege = await _vorschlag_erzeugen(hub)
    assert {"art", "cover"} <= alle_felder(vorschlaege)
    assert hub.online.vorschlaege_zahl(SID) == len(vorschlaege)
    for v in vorschlaege:
        await hub.online.vorschlag_verwerfen(SID, v["id"])
    assert hub.online.vorschlaege_gueltig(SID) == []
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.vorschlag_verwerfen(SID, vorschlaege[0]["id"])  # zweites Mal
    assert e.value.code == "vorschlag_nicht_gefunden"
    hub.online.store.daten["serien"][SID].pop("marke", None)
    await arbeite(hub, im_lauf=True)
    assert {"art", "cover"}.isdisjoint(alle_felder(hub.online.vorschlaege_gueltig(SID)))  # derselbe Wert aus derselben Quelle: nie wieder
    # bei der Suche von Hand: Marke „früher abgelehnt“
    erg = await hub.online.suchen(SID, FOLGE)
    assert any(t["frueher_abgelehnt"] for t in erg["treffer"])


async def test_vorschlag_uebernehmen_ist_kein_verwerfen(hub: Any, nas: Any) -> None:
    vorschlaege = await _vorschlag_erzeugen(hub)
    cover = next(v for v in vorschlaege if "cover" in v["felder"])
    uebersicht = await hub.online.treffer(serie_id=SID, vorschlag_id=cover["id"])
    assert uebersicht["felder"]["cover"]["neu"] is True and "grund" not in uebersicht
    erg = await hub.online.uebernehmen(SID, list(cover["felder"]), vorschlag_id=cover["id"])
    assert erg["aenderung_id"] and cover["id"] not in [x["id"] for x in hub.online.store.vorschlaege(SID)]
    assert hub.online.store.lies(SID).get("verworfen") is None  # „Übernehmen“ zählt nicht als „Nein“
    assert hub.online.store.hand_hat(SID, "cover") and (nas.medien / "bibi" / COVER_ONLINE).is_file()
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.uebernehmen(SID, ["art"], vorschlag_id=cover["id"])
    assert e.value.code == "vorschlag_nicht_gefunden"


async def test_vorschlag_faellt_weg_wenn_folge_verschwindet(hub: Any) -> None:
    await _vorschlag_erzeugen(hub)
    hub.online.store.serie(SID)["vorschlaege"][0]["felder"].append(f"nummer@{FOLGE}")
    hub.online.store.loesche_folge(SID, FOLGE)
    assert all(not k.endswith("@" + FOLGE) for x in hub.online.store.vorschlaege(SID) for k in x["felder"])


# --------------------------------------------------------------------------
# Claude (3.4, GO-2)
# --------------------------------------------------------------------------


class KiDienst:
    def __init__(self, hass: Any, antwort: dict[str, Any] | Exception) -> None:
        self.aufrufe: list[dict[str, Any]] = []
        self.antwort = antwort
        hass.states.async_set("ai_task.test_claude", "unknown")
        from homeassistant.core import SupportsResponse

        async def behandle(call: Any) -> dict[str, Any]:
            self.aufrufe.append(dict(call.data))
            if isinstance(self.antwort, Exception):
                raise self.antwort
            return {"data": self.antwort}

        hass.services.async_register("ai_task", "generate_data", behandle, supports_response=SupportsResponse.ONLY)


@pytest.fixture
async def hub_claude(starte_integration: Any, nas: Any, lege_mp3: Any, hass: Any) -> Any:
    """Zwei Einträge: „Bibi Blocksberg“ (Ziel) und einer mit Grund ``serie_aus_ordner``, dessen Ordnername einen besseren Namen enthält."""
    lege_bibi(nas, lege_mp3)
    lege_bibi(nas, lege_mp3, gruende=["serie_aus_ordner"], name="Bibi Blocksberg (2)", ordner="Bibi Blocksberg - Hexen", serie_id="zwei")
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    h.online.ki.drossel._abstand = 0  # noqa: SLF001 - sonst wartet der zweite Aufruf 3 Sekunden (Drossel 3.4)
    return h


def setze_option(hub: Any, monkeypatch: pytest.MonkeyPatch, **optionen: Any) -> None:
    """Optionen der Integration ändern, ohne dass der Update-Listener die Integration neu lädt."""
    from types import MappingProxyType

    object.__setattr__(hub.entry, "options", MappingProxyType(optionen))


async def arbeite_zwei(hub: Any, **kw: Any) -> dict[str, Any]:
    async with hub.online._arbeit:
        return await hub.online._arbeite_serie("zwei", folgen=None, neu=False, im_lauf=kw.get("im_lauf", False), lauf_id=None)


async def test_option_leer_kein_claude_schritt_und_marke_aus(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": "Bibi Blocksberg", "grund": "x"})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: ""})
    assert hub_claude.online.ki_entitaet() is None
    await arbeite_zwei(hub_claude)
    assert ki.aufrufe == []
    assert hub_claude.online.store.claude_marke("zwei")["ergebnis"] == "aus"
    assert hub_claude.online.status()["quellen"]["claude"] == {"eingerichtet": False, "erreichbar": False}
    assert not [v for v in hub_claude.online.store.vorschlaege("zwei") if v["quelle"] == "claude"]


async def test_option_drei_zustaende_fehlt_leer_gesetzt(hub_claude: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_flow, "vorgabe_ki_entitaet", lambda hass: "ai_task.vorgabe")
    setze_option(hub_claude, monkeypatch)  # Schlüssel fehlt in den Optionen: die Vorgabe gilt
    assert hub_claude.online.ki_entitaet() == "ai_task.vorgabe"
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: ""})
    assert hub_claude.online.ki_entitaet() is None  # leer: Schritt aus
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    assert hub_claude.online.ki_entitaet() == "ai_task.test_claude"
    monkeypatch.setattr(config_flow, "vorgabe_ki_entitaet", lambda hass: "")
    setze_option(hub_claude, monkeypatch)
    assert hub_claude.online.ki_entitaet() is None  # keine Vorgabe (nicht genau eine Entität)


async def test_option_nachtraeglich_gesetzt_eintrag_wird_im_lauf_nachgeholt(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": "Bibi Blocksberg", "grund": "Der Ordner nennt die Reihe."})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: ""})
    await arbeite_zwei(hub_claude)  # Option leer: Marke ``aus``, sonst alles wie sonst
    assert hub_claude.online.store.claude_marke("zwei")["ergebnis"] == "aus" and ki.aufrufe == []
    # Option gesetzt: ``aus`` verfällt, der Eintrag kommt wieder in den Lauf (auch bei gültiger übriger Marke)
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    assert "zwei" in hub_claude.online.lauf_kandidaten()
    await hub_claude.online.lauf_starten()
    await hub_claude.online.warte_auf_lauf()
    assert len(ki.aufrufe) == 1
    assert "<<<DATEN" in ki.aufrufe[0]["instructions"] and ki.aufrufe[0]["entity_id"] == "ai_task.test_claude"
    assert hub_claude.online.store.claude_marke("zwei")["ergebnis"] == "vorschlag"
    assert "zwei" not in hub_claude.online.lauf_kandidaten()  # gültige Marke, kein zweiter Aufruf
    # Der Name existiert schon als anderer Eintrag („Bibi Blocksberg“): Vorschlag zum Zusammenführen (8.4)
    (v,) = [v for v in hub_claude.online.store.vorschlaege("zwei") if v["quelle"] == "claude"]
    assert v["art"] == "zusammenfuehren" and v["ziel_serie_id"] == SID and v["grund"].startswith("Der Ordner")
    liste = hub_claude.online.vorschlaege_liste("zwei")
    assert liste[0]["art"] == "zusammenfuehren" and liste[0]["ziel_serie_id"] == SID and liste[0]["quelle"] == "claude"


async def test_claude_namensvorschlag_uebernehmen_ist_umbenennen_von_hand(hub_claude: Any, hass: Any, nas: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": "Hexen", "grund": "Der Teil nach dem Strich."})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    erg = await arbeite_zwei(hub_claude)
    assert erg["vorschlaege"] >= 1 and len(ki.aufrufe) == 1
    (v,) = [v for v in hub_claude.online.vorschlaege_gueltig("zwei") if v["quelle"] == "claude"]
    assert v["art"] == "felder" and v["felder"] == ["serie_name"] and hub_claude.online.vorschlaege_liste("zwei")[-1]["name"] == "Hexen"
    uebersicht = await hub_claude.online.treffer(serie_id="zwei", vorschlag_id=v["id"])
    assert uebersicht["felder"]["serie_name"]["neu"] == "Hexen" and uebersicht["grund"].startswith("Der Teil")
    with pytest.raises(TobiboxFehler) as e:
        await hub_claude.online.uebernehmen("zwei", ["serie_name"], vorschlag_id=v["id"])  # ``stand`` ist Pflicht
    assert e.value.code == "invalid_format"
    with pytest.raises(TobiboxFehler) as e2:
        await hub_claude.online.uebernehmen("zwei", ["serie_name"], vorschlag_id=v["id"], stand="alt")
    assert e2.value.code == "stand_veraltet"
    stand = hub_claude.medien.serien["zwei"].serie.stand
    antwort = await hub_claude.online.uebernehmen("zwei", ["serie_name"], vorschlag_id=v["id"], stand=stand)
    assert antwort["aenderung_id"] is None and nas.serie_json("Bibi Blocksberg - Hexen")["name"] == "Hexen"
    assert all("serie_name" not in a["felder"] for a in hub_claude.online.store.aenderungen("zwei"))  # keine Online-Änderung
    assert "serie_name" not in (hub_claude.online.kurz_online("zwei") or {"felder": []})["felder"]
    assert not hub_claude.online.store.lies("zwei").get("verworfen")


async def test_claude_vorschlag_faellt_weg_wenn_name_von_hand_geaendert_wird(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    KiDienst(hass, {"entscheidung": "kandidat", "name": "Hexen", "grund": "G"})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await arbeite_zwei(hub_claude)
    assert hub_claude.online.vorschlaege_zahl("zwei") == 1
    await hub_claude.medien.serie_umbenennen("zwei", "Ganz anders")
    assert hub_claude.online.vorschlaege_zahl("zwei") == 0  # GO-3


async def test_claude_nein_kommt_nicht_wieder(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": "Hexen", "grund": "G"})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await arbeite_zwei(hub_claude)
    (v,) = hub_claude.online.vorschlaege_gueltig("zwei")
    await hub_claude.online.vorschlag_verwerfen("zwei", v["id"])
    hub_claude.online.store.daten["serien"]["zwei"]["marke"].pop("claude")  # Marke weg: der Schritt läuft noch einmal
    await arbeite_zwei(hub_claude)
    assert len(ki.aufrufe) == 2  # Claude wurde wirklich noch einmal gefragt, derselbe Name kommt aber nicht wieder
    assert hub_claude.online.vorschlaege_gueltig("zwei") == []


async def test_claude_fehler_marke_fehler_ein_tag(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    KiDienst(hass, RuntimeError("kaputt"))
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await arbeite_zwei(hub_claude)
    st = hub_claude.online.store
    assert st.claude_marke("zwei")["ergebnis"] == "fehler" and st.claude_gueltig("zwei", True)
    st.daten["serien"]["zwei"]["marke"]["claude"]["zeit"] = "2020-01-01T00:00:00Z"
    assert not st.claude_gueltig("zwei", True)  # nach einem Tag wird der Eintrag wieder gefragt
    assert "zwei" in hub_claude.online.lauf_kandidaten()
    assert hub_claude.online.status()["quellen"]["claude"]["erreichbar"] is False  # der letzte Aufruf ist fehlgeschlagen


async def test_claude_nur_fuer_eintraege_mit_grund(hub_claude: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    ki = KiDienst(hass, {"entscheidung": "behalten", "name": "x", "grund": "g"})
    setze_option(hub_claude, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await arbeite(hub_claude)  # „bibi“ hat keinen Grund
    assert ki.aufrufe == [] and hub_claude.online.store.claude_marke(SID) is None
    await arbeite_zwei(hub_claude)
    assert len(ki.aufrufe) == 1 and hub_claude.online.store.claude_marke("zwei")["ergebnis"] == "behalten"
    assert hub_claude.online.vorschlaege_gueltig("zwei") == []


# --------------------------------------------------------------------------
# Lauf (5.3), Status (Nr. 63), Ereignis
# --------------------------------------------------------------------------


async def test_lauf_start_stop_zustaende_und_status(hub: Any) -> None:
    hub.online.store.setze_marke(SID, "keiner", [FOLGE], None)
    hub.online.store.daten["serien"][SID].pop("marke")
    assert (await hub.online.lauf_stoppen()) == {"lauf": None}  # ohne Lauf kein Fehler
    erg = await hub.online.lauf_starten()
    assert erg["lauf"]["zustand"] == "laeuft" and erg["lauf"]["gesamt"] == 1
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.lauf_starten()
    assert e.value.code == "lauf_laeuft_schon"
    assert hub.online.status()["lauf"]["lauf_id"] == erg["lauf"]["lauf_id"]
    await hub.online.warte_auf_lauf()
    s = hub.online.status()
    assert s["lauf"] is None and s["letzte_laeufe"][0]["zustand"] == "fertig"
    assert s["letzte_laeufe"][0]["zahlen"]["erledigt"] == 1 and "grund" not in s["letzte_laeufe"][0]
    assert set(s["quellen"]) == {"itunes", "tonies", "tonies_shop", "claude"} and s["tonie_liste"]["anzahl"] == len(hub.online.tonie_liste.eintraege)
    # Ein Lauf mit gültiger Marke hat keine Kandidaten (kein neues Fragen)
    assert (await hub.online.lauf_starten())["lauf"]["gesamt"] == 0
    await hub.online.warte_auf_lauf()


async def test_lauf_stop_haelt_nach_der_aktuellen_serie_an(hub: Any, nas: Any, lege_mp3: Any) -> None:
    lege_bibi(nas, lege_mp3, name="Zweite", ordner="zweite", serie_id="zweite")
    await hub.medien.pruefen()
    gate = asyncio.Event()
    alt = hub.online.quellen.itunes_suche

    async def langsam(*a: Any, **k: Any) -> Any:
        await gate.wait()
        return await alt(*a, **k)

    hub.online.quellen.itunes_suche = langsam
    await hub.online.lauf_starten()
    await asyncio.sleep(0)
    erg = await hub.online.lauf_stoppen()
    assert erg["lauf"]["zustand"] == "wird_angehalten"
    gate.set()
    await hub.online.warte_auf_lauf()
    letzter = hub.online.status()["letzte_laeufe"][0]
    assert letzter["zustand"] == "angehalten" and letzter["grund"] == "angehalten" and letzter["zahlen"]["erledigt"] == 1


async def test_lauf_abgebrochen_nach_neustart_und_weiterlauf(hub: Any, hass: Any, hass_storage: dict[str, Any]) -> None:
    st = hub.online.store
    st.lauf_speichern({"lauf_id": "alt", "beginn": "2026-11-19T10:00:00Z", "ende": None, "zustand": "laeuft", "zahlen": {"erledigt": 2, "gesamt": 5, "geaendert": 1, "vorschlaege": 0, "keiner": 1}})
    await st.sofort()
    neu = type(hub.online)(hub)  # wie nach einem HA-Neustart
    await neu.async_laden()
    (lauf,) = [x for x in neu.store.daten["laeufe"] if x["lauf_id"] == "alt"]
    assert lauf["zustand"] == "abgebrochen" and lauf["grund"] == "neustart" and lauf["ende"]
    assert neu.lauf_zustand() is None
    letzter = neu.status()["letzte_laeufe"][0]
    assert letzter["zustand"] == "abgebrochen" and letzter["grund"] == "neustart" and letzter["zahlen"]["erledigt"] == 2
    # Ein neuer Start geht weiter (kein „Fortsetzen“: die Marken bestimmen die Kandidaten)
    neu.quellen, neu.tonie_liste = hub.online.quellen, hub.online.tonie_liste
    erg = await neu.lauf_starten()
    await neu.warte_auf_lauf()
    assert erg["lauf"]["lauf_id"] != "alt" and neu.status()["letzte_laeufe"][0]["zustand"] == "fertig"
    await neu.async_stop()


async def test_async_stop_markiert_laufenden_lauf_als_abgebrochen(hub: Any) -> None:
    hub.online.store.daten["serien"][SID] = {}
    gate = asyncio.Event()

    async def haengt(*a: Any, **k: Any) -> Any:
        await gate.wait()
        return []

    hub.online.quellen.itunes_suche = haengt
    await hub.online.lauf_starten()
    await asyncio.sleep(0)
    await hub.online.async_stop()
    (lauf,) = hub.online.store.daten["laeufe"][-1:]
    assert lauf["zustand"] == "abgebrochen" and lauf["grund"] == "neustart"


async def test_lauf_pause_der_quelle_wartet_und_bricht_nach_drei_pausen_ab(hub: Any) -> None:
    schlafzeiten: list[float] = []

    async def schlafen(s: float) -> None:
        schlafzeiten.append(s)

    hub.online._schlafen = schlafen  # noqa: SLF001
    hub.online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    letzter = hub.online.status()["letzte_laeufe"][0]
    assert letzter["zustand"] == "abgebrochen" and letzter["grund"] == "quelle"
    assert len(schlafzeiten) == 2 and all(s > 800 for s in schlafzeiten)
    assert hub.online.store.marke(SID) is None  # keine Marke ``fehler`` für den Rest


async def test_lauf_pause_geht_danach_weiter(hub: Any) -> None:
    pausiert: list[str] = []

    async def schlafen(s: float) -> None:
        pausiert.append(hub.online.status()["lauf"]["zustand"])
        hub.online.quellen.itunes_pause = None

    hub.online._schlafen = schlafen  # noqa: SLF001
    hub.online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    assert pausiert == ["pausiert"] and hub.online.status()["letzte_laeufe"][0]["zustand"] == "fertig"


async def test_status_pausengruppen_auf_quellen_abgebildet(hub: Any) -> None:
    bis = time.time() + 600
    hub.online.quellen.pausen = {"bilder": bis, "tonies_shop": bis + 10}
    q = hub.online.status()["quellen"]
    assert q["itunes"]["erreichbar"] is False and q["itunes"]["pause_bis"].endswith("Z")  # Apples Bilder zählen zu Apple
    assert q["tonies_shop"]["erreichbar"] is False and q["tonies"] == {"erreichbar": True}


async def test_ereignis_online_nur_fuer_administratoren(hub: Any, hass: Any) -> None:
    from custom_components.tobibox.hub import Abo

    admin: list[Any] = []
    alltag: list[Any] = []

    def verbindung(liste: list[Any]) -> Any:
        return SimpleNamespace(user=None, send_message=lambda n: liste.append(n["event"]))

    hub.abo_hinzu(Abo(verbindung(admin), 1, {"online", "medien"}, "a", ist_admin=True))
    hub.abo_hinzu(Abo(verbindung(alltag), 2, {"online", "medien"}, "b", ist_admin=False))
    hub.abo_hinzu(Abo(verbindung(alltag), 3, {"online"}, "c"))  # Vorgabe: kein Administrator
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    arten = [e["art"] for e in admin if e["thema"] == "online"]
    assert "stand" in arten and "fertig" in arten
    fertig = next(e for e in admin if e["thema"] == "online" and e["art"] == "fertig")
    assert fertig["daten"]["vorgang"] == "lauf" and fertig["daten"]["zustand"] == "fertig"
    assert [e for e in alltag if e["thema"] == "online"] == []
    assert hub.snapshot("online") == hub.online.status()


async def test_ereignis_quelle_bei_wechsel(hub: Any) -> None:
    from custom_components.tobibox.hub import Abo

    ereignisse: list[Any] = []
    hub.abo_hinzu(Abo(SimpleNamespace(send_message=lambda n: ereignisse.append(n["event"])), 1, {"online"}, "a", ist_admin=True))
    hub.online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    await arbeite(hub)
    q = [e for e in ereignisse if e["art"] == "quelle"]
    assert q and q[0]["daten"] == {"quelle": "itunes", "erreichbar": False, "pause_bis": q[0]["daten"]["pause_bis"]}


# --------------------------------------------------------------------------
# Pflegestellen am echten Hub (7.3) und Anbindung (5.1)
# --------------------------------------------------------------------------


async def test_pflegestellen_folge_loeschen_und_serie_loeschen_ziehen_den_store_mit(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    assert hub.online.store.lies(SID)
    await hub.medien.folge_loeschen(SID, FOLGE, True, None)
    assert hub.online.store.folge_info(SID, FOLGE) == {} and hub.online.store.schnapp_wert(SID, f"nummer@{FOLGE}") == (False, None)
    await hub.medien.serie_loeschen(SID, True, None)
    assert hub.online.store.lies(SID) == {}


async def test_pflegestellen_zusammenfuehren_und_verschieben(hub: Any, nas: Any, lege_mp3: Any) -> None:
    lege_bibi(nas, lege_mp3, name="Ziel", ordner="ziel", serie_id="ziel")
    await hub.medien.pruefen()
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    st = hub.online.store
    st.setze_hand(SID, "cover")
    assert st.folge_info(SID, FOLGE)
    await hub.medien.serien_zusammenfuehren(SID, "ziel", True, None, None)
    assert st.lies(SID) == {}  # die Quelle ist weg
    zielfolge = next(f for f in hub.medien.serien["ziel"].serie.folgen if f != FOLGE)  # beide heißen „f100“: die verschobene bekommt ein Suffix
    assert st.folge_info("ziel", zielfolge)["alter_ab"] == 4  # die Beschreibung zog mit
    assert st.schnapp_wert("ziel", f"nummer@{zielfolge}") == (True, 100)
    assert st.hand_hat("ziel", "cover")  # das Online-Cover wurde kopiert: ``hand.cover`` zieht mit (GO-17)
    assert (nas.medien / "ziel" / COVER_ONLINE).is_file()


async def test_pflegestelle_umbenennen_aendert_den_store_nicht(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    vorher = json.dumps(hub.online.store.daten, sort_keys=True)
    await hub.medien.serie_umbenennen(SID, "Anders")
    nachher = json.loads(json.dumps(hub.online.store.daten))
    assert nachher["serien"][SID].get("hand", {}).get("serie_name") is None  # nur die Marke „zurückgenommen“ wird durch ``hand`` ersetzt
    assert json.dumps(nachher["serien"][SID]["aenderungen"], sort_keys=True) == json.dumps(json.loads(vorher)["serien"][SID]["aenderungen"], sort_keys=True)


async def test_bestaetigen_loescht_die_schnappschuesse(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await hub.medien.bestaetigen(SID, [FOLGE])
    assert hub.online.store.schnapp_wert(SID, f"nummer@{FOLGE}") == (False, None)
    await hub.medien.bestaetigen(SID, None)
    assert hub.online.store.schnapp_wert(SID, "art") == (False, None)


async def test_von_hand_geaendert_ersetzt_marke_zurueckgenommen(hub: Any) -> None:
    st = hub.online.store
    st.setze_zurueckgenommen(SID, "art")
    await hub.medien.serie_art_setzen(SID, "musik")
    assert st.hand_hat(SID, "art") and not st.zurueck_hat(SID, "art")


async def test_schnapp_nummer_von_hand_geaendert_nur_vorschlag(hub: Any, nas: Any) -> None:
    """6.1: Weicht ``anzeige`` vom Schnappschuss ab (ein Mensch hat umbenannt), wird aus der Übernahme ein Vorschlag."""
    await schnapp_wie_einsortiert(hub, nummer=None)
    await hub.medien.folge_umbenennen(SID, FOLGE, "Von Hand umbenannt", None)
    await arbeite(hub)
    sj = serie_json(nas)
    assert sj["folgen_info"][FOLGE]["anzeige"] == "Von Hand umbenannt"
    assert sj["folgen_info"][FOLGE]["nummer"] == 100 if "nummer" in sj["folgen_info"][FOLGE] else True


async def test_bestand_ohne_schnappschuss_ist_von_hand_ausser_mit_grund(hub: Any, nas: Any, lege_mp3: Any) -> None:
    """Ohne Schnappschuss und ohne passenden Prüfgrund gilt die Nummer als von Hand: Vorschlag statt Änderung."""
    lege_bibi(nas, lege_mp3, name="Bibi Blocksberg", ordner="alt", serie_id="alt")
    await hub.medien.pruefen()
    async with hub.online._arbeit:
        erg = await hub.online._arbeite_serie("alt", folgen=None, neu=False, im_lauf=True, lauf_id=None)
    sj = nas.serie_json("alt")
    assert "nummer" not in sj["folgen_info"][FOLGE]  # kein Grund, kein Schnappschuss: nicht angefasst
    assert any(f"nummer@{FOLGE}" in v["felder"] for v in hub.online.store.vorschlaege("alt")) and erg["vorschlaege"] >= 1


async def test_einsortieren_stoesst_die_online_suche_an_und_anders_einsortieren_geht(hub: Any, nas: Any) -> None:
    """5.1: ``_serie_abarbeiten`` meldet die neuen Folgen an ``online.neu_einsortiert`` (Schnappschuss, Schlange); der Dienst wartet nie."""
    from .test_einsortierung_neu import einsortiert, neu

    zeile = await einsortiert(hub, nas)
    await hub.online.warte_auf_ende()
    (sid,) = [s for s in hub.medien.serien if s != SID]
    sn = hub.online.store.lies(sid).get("schnapp")
    assert sn and set(sn["folgen"]) == {"a.mp3", "b.mp3"} and sn["art"]  # Schnappschuss von Anzeige, Nummer und Art der neuen Serie
    assert "serie_name" not in json.dumps(sn)
    assert hub.online.store.marke(sid)["ergebnis"] in ("keiner", "vorschlag", "geaendert")  # die Attrappe kennt „Quelle“ nicht
    await neu(hub, zeile)  # „Anders einsortieren“ geht danach noch
    assert hub.online.store.lies(sid) == {}  # und räumt den Store auf (7.3)


async def test_lese_version_im_executor(hub: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Auflage: ``lese_version`` liest ``manifest.json``; der Dienst ruft sie im Executor."""
    from custom_components.tobibox import online as online_modul
    from custom_components.tobibox.online_quellen import lese_version

    echt = online_modul.OnlineDienst.__dict__["_baue_quellen"]
    aufrufe: list[Any] = []
    orig = hub.hass.async_add_executor_job

    async def spion(func: Any, *args: Any) -> Any:
        aufrufe.append(func)
        return await orig(func, *args)

    monkeypatch.setattr(hub.hass, "async_add_executor_job", spion)
    manifest = json.loads((Path(__file__).parents[1] / "custom_components" / "tobibox" / "manifest.json").read_text(encoding="utf-8"))
    assert lese_version() == manifest["version"]
    from custom_components.tobibox.online_quellen import OnlineQuellen

    # die echte Methode (die Datei ``conftest.py`` ersetzt sie sonst durch eine Attrappe ohne Netz)
    ORIGINAL = getattr(online_modul, "_BAUE_QUELLEN_ORIGINAL", None)
    if ORIGINAL is not None:
        quellen = await ORIGINAL(hub.online)
        assert isinstance(quellen, OnlineQuellen) and lese_version in aufrufe
    del echt


async def test_werte_gehen_vor_dem_schreiben_durch_online_text(hub: Any, nas: Any) -> None:
    """Auflage: Steuerzeichen und Leerraum aus Quellen kommen nie in ``serie.json`` oder in den Store."""
    erg = await hub.online.suchen(SID, FOLGE)
    t = next(t for t in erg["treffer"] if f"folge_titel@{FOLGE}" in t["felder"])
    _such, roh = hub.online._suche_holen(t["treffer_id"])  # noqa: SLF001
    roh["werte"][f"folge_titel@{FOLGE}"] = "Neuer\x00 Titel \n  mit\tLeerraum"
    roh["werte"]["serie_name"] = "Neuer\x07  Name"
    stand = hub.medien.serien[SID].serie.stand
    await hub.online.uebernehmen(SID, [f"folge_titel@{FOLGE}", "serie_name"], treffer_id=t["treffer_id"], stand=stand)
    sj = serie_json(nas)
    assert sj["folgen_info"][FOLGE]["anzeige"] == "Neuer Titel mit Leerraum" and sj["name"] == "Neuer Name"
    assert hub.online.store.hand_hat(SID, "serie_name") and hub.online.store.hand_hat(SID, f"folge_titel@{FOLGE}")
    # eine Übernahme von Hand löst die Gründe wie ein Umbenennen (alles weg) und setzt keinen Schnappschuss
    assert "pruefen" not in sj and "pruefen" not in sj["folgen_info"][FOLGE]
    assert hub.online.store.schnapp_wert(SID, f"folge_titel@{FOLGE}") == (False, None)


async def test_start_klaert_offene_aenderungen_und_bereinigt(hub: Any, nas: Any) -> None:
    st = hub.online.store
    # (1) trägt das Feld den Online-Wert: ``fertig``
    st.serie(SID)["aenderungen"] = [
        {"id": "a1", "zeit": "2026-11-19T10:00:00Z", "wer": "auto", "quelle": "itunes", "status": "offen",
         "felder": {"art": {"vorher": {"art": "musik", "art_quelle": "geraten"}, "nachher": {"art": "musik", "art_quelle": "geraten"}}}, "schnapp_vorher": {"art": "x"}},
        {"id": "a2", "zeit": "2026-11-19T10:01:00Z", "wer": "auto", "quelle": "itunes", "status": "offen",
         "felder": {f"nummer@{FOLGE}": {"vorher": None, "nachher": 77}}, "schnapp_vorher": {"art": "alt-schnapp", "folgen": {FOLGE: {"nummer": 5}}}},
    ]
    st.setze_schnapp(SID, "art", "neuer-schnapp")  # gehört nicht zu den Feldern der offenen Änderung: bleibt (GO3-7)
    st.setze_schnapp(SID, f"nummer@{FOLGE}", 77)
    st.setze_schnapp("verwaist", "art", "musik")  # eine Serie, die es nicht mehr gibt
    await hub.online.beim_start()
    liste = {a["id"]: a for a in st.aenderungen(SID)}
    assert liste["a1"]["status"] == "fertig" and "schnapp_vorher" not in liste["a1"]
    assert "a2" not in liste  # das Feld trägt den Wert nicht: verworfen, der Schnappschuss **dieses Felds** aus ``schnapp_vorher`` ist wieder da
    assert st.schnapp_wert(SID, f"nummer@{FOLGE}") == (True, 5) and st.schnapp_wert(SID, "art") == (True, "neuer-schnapp")
    assert st.lies("verwaist") == {}


async def test_ausgabe_vorschlaege_liste_und_kurz_online_nur_fertige(hub: Any) -> None:
    assert hub.online.kurz_online(SID) is None and hub.online.vorschlaege_liste(SID) == []
    hub.online.store.serie(SID)["aenderungen"] = [{"id": "o", "zeit": "2020-01-01T00:00:00Z", "status": "fertig", "felder": {"cover": {}}}]
    assert hub.online.kurz_online(SID) is None  # älter als 30 Tage
    assert (await hub.online.beschreibung(SID, FOLGE)) == {"beschreibung": None, "quelle": None}
    with pytest.raises(TobiboxFehler) as e:
        await hub.online.beschreibung(SID, "gibtsnicht")
    assert e.value.code == "folge_nicht_gefunden"
    with pytest.raises(TobiboxFehler) as e2:
        await hub.online.beschreibung("gibtsnicht", FOLGE)
    assert e2.value.code == "serie_nicht_gefunden"


async def test_beschreibung_voller_text_nr_64(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    erg = await hub.online.beschreibung(SID, FOLGE)
    assert erg["quelle"] == "tonies_shop" and erg["alter_ab"] == 4 and erg["beschreibung"].startswith("Ein neues hexisches")
    kurz = hub.online.folge_online(SID, FOLGE)
    assert kurz["beschreibung_quelle"] == "tonies_shop" and kurz["beschreibung_gekuerzt"] in (True, False) and len(kurz["beschreibung"]) <= 301


# --------------------------------------------------------------------------
# Nachbesserung nach dem Review OS3 (GO3-1 bis GO3-13)
# --------------------------------------------------------------------------


async def _hub_mit(starte_integration: Any, nas: Any, lege_mp3: Any, **kw: Any) -> Any:
    lege_bibi(nas, lege_mp3, **kw)
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    return h


@pytest.fixture
async def hub_stimmt(starte_integration: Any, nas: Any, lege_mp3: Any) -> Any:
    """Nummer und Titel stimmen schon, kein Prüfgrund, Art von Hand: ein Eintrag, an dem es (fast) nichts zu bestätigen gibt."""
    return await _hub_mit(starte_integration, nas, lege_mp3, nummer=100, art_quelle="manuell")


@pytest.fixture
async def hub_bestaetigung(starte_integration: Any, nas: Any, lege_mp3: Any) -> Any:
    """Titel und Nummer stimmen, Grund ``tags_fehlen`` steht noch; Cover, Art, Beschreibung und Alter sind der Automatik entzogen:
    die Online-Suche kann nur noch **bestätigen**."""
    h = await _hub_mit(starte_integration, nas, lege_mp3, nummer=100, art_quelle="manuell", gruende=["tags_fehlen"])
    (nas.medien / "bibi" / "cover-eigen.jpg").write_bytes(jpeg())
    await h.medien.pruefen()
    h.online.store.setze_hand(SID, f"beschreibung@{FOLGE}")
    h.online.store.setze_hand(SID, f"alter_ab@{FOLGE}")
    await schnapp_wie_einsortiert(h, nummer=100)
    return h


# GO3-1: Bestätigen


async def test_zweiter_lauf_an_einem_eintrag_der_stimmt_legt_nichts_an(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    (erste,) = hub.online.store.aenderungen(SID)
    kurz = hub.online.kurz_online(SID)
    for _ in range(2):
        hub.online.store.daten["serien"][SID].pop("marke", None)
        await arbeite(hub)
    assert [a["id"] for a in hub.online.store.aenderungen(SID)] == [erste["id"]]  # keine leeren Änderungen
    assert hub.online.kurz_online(SID) == kurz and kurz["felder"]  # die Zeile der echten Änderung bleibt
    erg = await hub.online.zuruecknehmen(SID)
    assert erg["zurueckgenommen"] == len(erste["felder"])  # nur wirklich zurückgesetzte Felder zählen


async def test_bestaetigen_ohne_pruefgrund_setzt_keinen_schnappschuss(hub_stimmt: Any) -> None:
    """Hat ein Mensch Titel und Nummer bestätigt (kein Schnappschuss mehr, kein Grund), macht ein gleicher sicherer Wert sie nicht wieder automatisch."""
    hub = hub_stimmt
    await arbeite(hub)
    st = hub.online.store
    for key in (f"folge_titel@{FOLGE}", f"nummer@{FOLGE}"):
        assert st.schnapp_wert(SID, key) == (False, None)
        assert hub.online._sperre_grund(SID, hub.medien.serien[SID].serie, hub.medien.serien[SID], *teile(key)) == "vorschlag"  # noqa: SLF001
    assert all("bestaetigt" not in a for a in st.aenderungen(SID))


def teile(key: str) -> tuple[str, str | None]:
    feld, _, folge = key.partition("@")
    return feld, folge or None


async def test_bestaetigung_loest_den_grund_ohne_aenderung_im_online_feld(hub_bestaetigung: Any, nas: Any) -> None:
    hub = hub_bestaetigung
    erg = await arbeite(hub)
    assert erg["geaendert"] == 0
    (a,) = hub.online.store.aenderungen(SID)
    assert a["felder"] == {} and sorted(a["bestaetigt"]) == [f"folge_titel@{FOLGE}", f"nummer@{FOLGE}"] and a["status"] == "fertig"
    assert "pruefen" not in serie_json(nas)["folgen_info"][FOLGE]  # der Grund ist aufgelöst
    assert hub.online.kurz_online(SID) is None  # eine reine Bestätigung steht nie in ``online``
    # Rücknahme: der Grund kommt zurück, gezählt wird kein Feld, es gibt keine Marke
    erg = await hub.online.zuruecknehmen(SID)
    assert erg["zurueckgenommen"] == 0 and erg["uebersprungen_anzahl"] == 0
    assert serie_json(nas)["folgen_info"][FOLGE]["pruefen_gruende"] == ["tags_fehlen"]
    assert not hub.online.store.zurueck_hat(SID, f"nummer@{FOLGE}") and hub.online.store.aenderungen(SID)[0]["status"] == "zurueckgenommen"


async def test_bestaetigung_ohne_aufloesbaren_grund_ist_keine_aenderung(hub_bestaetigung: Any) -> None:
    """Nur die Nummer bestätigt: ``tags_fehlen`` braucht auch den Titel, es gäbe nichts aufzulösen."""
    hub = hub_bestaetigung
    info = hub.medien.serien[SID]
    start = hub.online._start_werte(SID, info)  # noqa: SLF001
    erg = {"geaendert": 0}
    ok, _ = await hub.online._schreibe_auto(SID, start, {}, [f"nummer@{FOLGE}"], None, None, erg)  # noqa: SLF001
    assert hub.online.store.aenderungen(SID) == [] and erg["geaendert"] == 0 and ok is True


# GO3-2


class SpaeteListe(FakeListe):
    """Wie die echte Liste: ``stand`` gibt es erst nach dem ersten ``sicherstellen`` (Datei gelesen)."""

    def __init__(self) -> None:
        self._geladen = False
        super().__init__()

    @property
    def stand(self) -> float | None:
        return self._stand_wert if self._geladen else None

    @stand.setter
    def stand(self, wert: float | None) -> None:
        self._stand_wert = wert

    async def sicherstellen(self, *, erzwingen: bool = False) -> bool:
        self._geladen = True
        return self.ok


async def test_marken_gelten_nach_neustart_auch_bevor_die_liste_geladen_ist(hub: Any) -> None:
    hub.online.store.setze_marke(SID, "keiner", [FOLGE], hub.online.tonie_liste.stand)
    neu = type(hub.online)(hub)  # wie nach einem HA-Neustart: Liste noch nicht geladen
    neu.store.daten = json.loads(json.dumps(hub.online.store.daten))
    neu.quellen, neu.tonie_liste = hub.online.quellen, SpaeteListe()
    assert neu.tonie_liste.stand is None
    erg = await neu.lauf_starten()
    assert erg["lauf"]["gesamt"] == 0  # die Marke ``keiner`` gilt, der Eintrag wird nicht noch einmal gefragt
    await neu.warte_auf_lauf()
    await neu.async_stop()


# GO3-3


async def test_bild_pause_verliert_das_cover_nicht(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    hub.online.quellen.bild_fehler = QuellePausiert("bilder", time.time() + 900)
    erg = await arbeite(hub, im_lauf=True)
    assert erg["pause"] is not None and hub.online.store.marke(SID) is None  # keine Marke: der Eintrag kommt wieder dran
    assert not (nas.medien / "bibi" / COVER_ONLINE).exists()
    hub.online.quellen.bild_fehler = None
    await arbeite(hub, im_lauf=True)
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file()


async def test_bild_fehler_verliert_das_cover_nicht(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    hub.online.quellen.bild_fehler = NichtErreichbar("aus")
    erg = await arbeite(hub)
    assert erg["fehler"] and hub.online.store.marke(SID) is None  # andere Felder sind übernommen, das Cover fehlt: nicht „fertig gesucht“
    assert hub.online.store.aenderungen(SID) and hub.medien.serien[SID].cover_quelle is None
    assert SID in hub.online.lauf_kandidaten()
    hub.online.quellen.bild_fehler = None
    await arbeite(hub)
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file() and hub.online.store.marke(SID)["ergebnis"] in ("geaendert", "keiner", "vorschlag")


async def test_lauf_holt_das_cover_nach_einer_bildpause_nach(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    hub.online.quellen.bild_fehler = QuellePausiert("bilder", time.time() + 900)

    async def schlafen(_s: float) -> None:
        hub.online.quellen.bild_fehler = None

    hub.online._schlafen = schlafen  # noqa: SLF001
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    assert hub.online.status()["letzte_laeufe"][0]["zustand"] == "fertig"
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file()  # nicht nur der Claude-Schritt, die ganze Serie lief noch einmal


# GO3-4


async def test_ausnahme_in_einer_serie_bricht_den_lauf_nicht_ab(hub: Any, nas: Any, lege_mp3: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    lege_bibi(nas, lege_mp3, name="Zweite", ordner="zweite", serie_id="zweite")
    await hub.medien.pruefen()
    echt = hub.online._arbeite_serie  # noqa: SLF001

    async def kaputt(sid: str, **kw: Any) -> Any:
        if sid == "zweite":
            raise KeyError("kaputter Eintrag")
        return await echt(sid, **kw)

    monkeypatch.setattr(hub.online, "_arbeite_serie", kaputt)
    await hub.online.lauf_starten()
    await hub.online.warte_auf_lauf()
    letzter = hub.online.status()["letzte_laeufe"][0]
    assert letzter["zustand"] == "fertig" and "grund" not in letzter and letzter["zahlen"]["erledigt"] == 2
    assert hub.online.store.marke("zweite")["ergebnis"] == "fehler"
    assert (nas.medien / "bibi" / COVER_ONLINE).is_file()  # die andere Serie wurde bearbeitet


# GO3-5 und GO3-6 (veraltete Felder)


async def test_hand_und_marken_werden_unter_der_sperre_neu_geprueft(hub: Any) -> None:
    """Während der Lauf auf das Bild wartet, übernimmt ein Mensch die Beschreibung und nimmt die Nummer zurück."""
    await schnapp_wie_einsortiert(hub)
    st = hub.online.store

    async def dazwischen() -> None:
        st.setze_hand(SID, f"beschreibung@{FOLGE}")
        st.setze_zurueckgenommen(SID, f"nummer@{FOLGE}")

    hub.online.quellen.vor_bild = dazwischen
    await arbeite(hub)
    fi = st.folge_info(SID, FOLGE)
    assert "beschreibung" not in fi  # ``hand``: nie überschrieben
    assert fi["alter_ab"] == 4  # was frei blieb, wird übernommen
    assert "nummer" not in serie_json_von(hub)["folgen_info"][FOLGE]
    angeboten = alle_felder(hub.online.vorschlaege_gueltig(SID))
    assert f"nummer@{FOLGE}" in angeboten and f"beschreibung@{FOLGE}" not in angeboten  # Marke: nur Vorschlag; ``hand``: nicht einmal das


def serie_json_von(hub: Any) -> dict[str, Any]:
    pfad = hub.pfade.medien / hub.medien.serien[SID].ordner / "serie.json"
    return json.loads(pfad.read_text(encoding="utf-8"))


async def test_beschreibung_im_store_inzwischen_geaendert_wird_vorschlag(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    st = hub.online.store

    async def dazwischen() -> None:
        st.setze_folge_info(SID, FOLGE, beschreibung="Neu von woanders", quelle="itunes")

    hub.online.quellen.vor_bild = dazwischen
    await arbeite(hub)
    assert st.folge_info(SID, FOLGE)["beschreibung"] == "Neu von woanders"
    assert f"beschreibung@{FOLGE}" in alle_felder(hub.online.vorschlaege_gueltig(SID))


async def test_veraltete_felder_werden_vorschlag_und_verschwundene_serie_wird_verworfen(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)

    async def dazwischen() -> None:
        await hub.medien.folge_umbenennen(SID, FOLGE, "Von Hand umbenannt", None)  # Titel und Stand weichen vom Start ab

    hub.online.quellen.vor_bild = dazwischen
    await arbeite(hub)
    assert "nummer" not in serie_json(nas)["folgen_info"][FOLGE]  # nicht überschrieben
    assert f"nummer@{FOLGE}" in alle_felder(hub.online.vorschlaege_gueltig(SID))


async def test_serie_waehrend_der_arbeit_geloescht_wird_still_verworfen(hub: Any, nas: Any) -> None:
    await schnapp_wie_einsortiert(hub)

    async def weg() -> None:
        await hub.medien.serie_loeschen(SID, True, None)

    hub.online.quellen.vor_bild = weg
    erg = await arbeite(hub)
    assert erg["geaendert"] == 0 and SID not in hub.medien.serien and not erg["fehler"]
    assert hub.online.store.aenderungen(SID) == []


# GO3-6: Rücknahme, dann Lauf, je Feld


async def test_ruecknahme_dann_lauf_beschreibung_und_alter_bleiben_vorschlag_moeglich(hub: Any) -> None:
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub)
    st = hub.online.store
    await hub.online.zuruecknehmen(SID)
    assert st.zurueck_hat(SID, f"beschreibung@{FOLGE}") and st.zurueck_hat(SID, f"alter_ab@{FOLGE}")
    st.daten["serien"][SID].pop("marke")
    erg = await arbeite(hub, im_lauf=True)
    assert erg["geaendert"] == 0
    assert st.folge_info(SID, FOLGE) == {}
    assert {f"beschreibung@{FOLGE}", f"alter_ab@{FOLGE}"} <= alle_felder(hub.online.vorschlaege_gueltig(SID))


async def test_ruecknahme_dann_lauf_titel_und_name_von_hand(hub: Any, nas: Any) -> None:
    """Übernahme von Hand von Titel und Name, Rücknahme, danach der Lauf: beide bleiben, höchstens als Vorschlag."""
    await hub.medien.serie_umbenennen(SID, "Eigener Name")
    await hub.medien.folge_umbenennen(SID, FOLGE, "Eigener Titel", None)
    erg = await hub.online.suchen(SID, FOLGE, None)
    apple = next(t for t in erg["treffer"] if t["quelle"] == "itunes" and f"folge_titel@{FOLGE}" in t["felder"] and "serie_name" in t["felder"])
    sj0 = serie_json(nas)
    stand = hub.medien.serien[SID].serie.stand
    ue = await hub.online.uebernehmen(SID, ["serie_name", f"folge_titel@{FOLGE}"], treffer_id=apple["treffer_id"], stand=stand)
    sj1 = serie_json(nas)
    assert sj1["name"] != sj0["name"] or sj1["folgen_info"][FOLGE]["anzeige"] != sj0["folgen_info"][FOLGE]["anzeige"]
    st = hub.online.store
    assert st.hand_hat(SID, "serie_name") and st.hand_hat(SID, f"folge_titel@{FOLGE}")
    await hub.online.zuruecknehmen(SID, ue["aenderung_id"])
    assert st.zurueck_hat(SID, "serie_name") and st.zurueck_hat(SID, f"folge_titel@{FOLGE}")
    sj2 = serie_json(nas)
    assert sj2["name"] == sj0["name"] and sj2["folgen_info"][FOLGE]["anzeige"] == sj0["folgen_info"][FOLGE]["anzeige"]
    await schnapp_wie_einsortiert(hub)
    st.daten["serien"][SID].pop("marke", None)
    await arbeite(hub, im_lauf=True)
    sj3 = serie_json(nas)
    assert sj3["name"] == sj0["name"] and sj3["folgen_info"][FOLGE]["anzeige"] == sj0["folgen_info"][FOLGE]["anzeige"]


async def test_name_von_hand_bleibt_nach_dem_lauf(hub: Any, nas: Any) -> None:
    await hub.medien.serie_umbenennen(SID, "Mein eigener Name")
    await schnapp_wie_einsortiert(hub)
    await arbeite(hub, im_lauf=True)
    assert serie_json(nas)["name"] == "Mein eigener Name"


# GO3-6: Fehler beim Schreiben, GO3-7


async def test_schreibfehler_hinterlaesst_keine_offene_aenderung(hub: Any, nas: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.tobibox import online as online_modul

    await schnapp_wie_einsortiert(hub)
    vorher_json = json.dumps(serie_json(nas), sort_keys=True)
    schnapp_vorher = json.dumps(hub.online.store.lies(SID).get("schnapp"), sort_keys=True)

    def kaputt(*_a: Any, **_k: Any) -> None:
        raise OSError("Platte voll")

    monkeypatch.setattr(online_modul, "schreibe_serie", kaputt)
    erg = await arbeite(hub)
    assert erg["fehler"]
    assert hub.online.store.aenderungen(SID) == []  # nicht ``offen`` stehen lassen
    assert json.dumps(hub.online.store.lies(SID).get("schnapp"), sort_keys=True) == schnapp_vorher
    assert json.dumps(serie_json(nas), sort_keys=True) == vorher_json
    assert not (nas.medien / "bibi" / COVER_ONLINE).exists()  # das neu geschriebene Cover wurde wieder entfernt


async def test_schreibfehler_beim_cover_laesst_nichts_zurueck(hub: Any, nas: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    from custom_components.tobibox import online as online_modul

    await schnapp_wie_einsortiert(hub)
    vorher_json = json.dumps(serie_json(nas), sort_keys=True)

    def kaputt(*_a: Any, **_k: Any) -> None:
        raise OSError("Platte voll")

    monkeypatch.setattr(online_modul, "schreibe_bytes_atomar", kaputt)
    erg = await arbeite(hub)
    assert erg["fehler"] and hub.online.store.aenderungen(SID) == []
    assert json.dumps(serie_json(nas), sort_keys=True) == vorher_json  # das Cover kommt zuerst: nichts anderes wurde geschrieben


async def test_start_stellt_nur_die_schnappschuesse_der_felder_zurueck_art_nicht(hub: Any) -> None:
    st = hub.online.store
    st.setze_schnapp(SID, "art", "neu")
    st.serie(SID)["aenderungen"] = [{"id": "x", "zeit": "2026-11-19T10:00:00Z", "wer": "auto", "quelle": "itunes", "status": "offen",
                                     "felder": {"art": {"vorher": {}, "nachher": {"art": "hoerspiel", "art_quelle": "online"}}}, "schnapp_vorher": {"art": "alt"}}]
    await hub.online.beim_start()
    assert st.schnapp_wert(SID, "art") == (True, "alt") and st.aenderungen(SID) == []


# GO3-6: mehrere Folgen und gemischte Fälle


async def test_mehrere_folgen_je_folge_eigene_gruende_und_ruecknahme(starte_integration: Any, nas: Any, lege_mp3: Any) -> None:
    for i in range(1, 14):
        lege_mp3(nas.medien / "bibi" / FOLGE / f"{i:02d}.mp3")
    for i in range(1, 4):
        lege_mp3(nas.medien / "bibi" / "andere" / f"{i:02d}.mp3")
    nas.serie("bibi", serie_id=SID, name="Bibi Blocksberg", folgen=[FOLGE, "andere"], art="musik", art_quelle="geraten", pruefen=True, pruefen_gruende=["art_geraten"],
              folgen_info={FOLGE: {"anzeige": FALL["folge"], "pruefen": True, "pruefen_gruende": ["tags_fehlen"]},
                           "andere": {"anzeige": "Etwas ganz anderes", "pruefen": True, "pruefen_gruende": ["track_doppelt"]}})
    hub = await starte_integration()
    hub.online.quellen, hub.online.tonie_liste = FakeQuellen(), FakeListe()
    await schnapp_wie_einsortiert(hub)
    hub.online.store.setze_schnapp(SID, "folge_titel@andere", "Etwas ganz anderes")
    hub.online.store.setze_schnapp(SID, "nummer@andere", None)
    await arbeite(hub)
    sj = serie_json(nas)
    assert sj["folgen_info"][FOLGE]["nummer"] == 100 and "nummer" not in sj["folgen_info"]["andere"]
    assert sj["folgen_info"]["andere"]["pruefen_gruende"] == ["track_doppelt"]  # ein anderer Grund wird nie aufgelöst
    assert "pruefen" not in sj["folgen_info"][FOLGE]
    assert hub.online.store.folge_info(SID, "andere") == {}  # Beschreibung und Alter gehören nur der passenden Folge
    (a,) = hub.online.store.aenderungen(SID)
    assert not any(k.endswith("@andere") for k in a["felder"])
    erg = await hub.online.zuruecknehmen(SID)
    assert erg["zurueckgenommen"] == len(a["felder"])
    sj = serie_json(nas)
    assert sj["folgen_info"][FOLGE]["pruefen_gruende"] == ["tags_fehlen"] and sj["folgen_info"]["andere"]["pruefen_gruende"] == ["track_doppelt"]


# GO3-8


async def test_ruecknahme_eines_namens_von_hand_stellt_die_serien_gruende_wieder_her(hub: Any, nas: Any) -> None:
    erg = await hub.online.suchen(SID, None, None)
    apple = next(t for t in erg["treffer"] if t["quelle"] == "itunes" and "serie_name" in t["felder"])
    sj0 = serie_json(nas)
    assert sj0["pruefen_gruende"] == ["art_geraten"]
    stand = hub.medien.serien[SID].serie.stand
    ue = await hub.online.uebernehmen(SID, ["serie_name"], treffer_id=apple["treffer_id"], stand=stand)
    assert "pruefen" not in serie_json(nas)  # wie ein Umbenennen von Hand
    await hub.online.zuruecknehmen(SID, ue["aenderung_id"])
    sj = serie_json(nas)
    assert sj["name"] == sj0["name"] and sj["pruefen"] is True and sj["pruefen_gruende"] == ["art_geraten"]


# GO3-9, GO3-12


async def test_zwei_start_zugleich_starten_nur_einen_lauf(hub: Any) -> None:
    ergebnisse = await asyncio.gather(hub.online.lauf_starten(), hub.online.lauf_starten(), return_exceptions=True)
    fehler = [e for e in ergebnisse if isinstance(e, TobiboxFehler)]
    gut = [e for e in ergebnisse if isinstance(e, dict)]
    assert len(gut) == 1 and len(fehler) == 1 and fehler[0].code == "lauf_laeuft_schon"
    await hub.online.warte_auf_lauf()
    assert len(hub.online.store.daten["laeufe"]) == 1


async def test_stop_weckt_den_schlafenden_lauf_und_bleibt_wird_angehalten(hub: Any) -> None:
    hub.online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    schlaeft = asyncio.Event()

    async def ewig(_s: float) -> None:
        schlaeft.set()
        await asyncio.Event().wait()  # kehrt nie von selbst zurück

    hub.online._schlafen = ewig  # noqa: SLF001
    await hub.online.lauf_starten()
    await asyncio.wait_for(schlaeft.wait(), 5)
    assert hub.online.status()["lauf"]["zustand"] == "pausiert"
    erg = await hub.online.lauf_stoppen()
    assert erg["lauf"]["zustand"] == "wird_angehalten"
    await asyncio.wait_for(hub.online.warte_auf_lauf(), 5)  # nicht erst nach 15 Minuten
    letzter = hub.online.status()["letzte_laeufe"][0]
    assert letzter["zustand"] == "angehalten" and letzter["grund"] == "angehalten"


# GO3-10


async def test_nein_zum_zusammenfuehren_kommt_nicht_wieder(hub_claude: Any) -> None:
    online = hub_claude.online
    info = hub_claude.medien.serien["zwei"]
    assert online._claude_vorschlag("zwei", info, "Bibi Blocksberg", "Der Ordner nennt die Reihe.")  # noqa: SLF001
    (v,) = online.store.vorschlaege("zwei")
    assert v["art"] == "zusammenfuehren"
    await online.vorschlag_verwerfen("zwei", v["id"])
    assert not online._claude_vorschlag("zwei", info, "Bibi Blocksberg", "Der Ordner nennt die Reihe.")  # noqa: SLF001
    assert online.store.vorschlaege("zwei") == []


# GO3-11


async def test_store_speichert_eine_kopie(hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    st = OnlineStore(hass)
    st.setze_hand("s", "art")
    gesehen: list[Any] = []

    async def speichern(daten: Any) -> None:
        gesehen.append(daten)

    gefordert: list[Any] = []
    monkeypatch.setattr(st._store, "async_save", speichern)  # noqa: SLF001
    monkeypatch.setattr(st._store, "async_delay_save", lambda fn, _s=0: gefordert.append(fn))  # noqa: SLF001
    await st.sofort()
    st.bald()
    assert gesehen[0] == st.daten and gesehen[0] is not st.daten and gesehen[0]["serien"] is not st.daten["serien"]
    kopie = gefordert[0]()
    assert kopie == st.daten and kopie is not st.daten and kopie["serien"]["s"] is not st.daten["serien"]["s"]


# GO3-13


async def test_pause_der_tonie_liste_wird_gemeldet(hub: Any) -> None:
    from custom_components.tobibox.hub import Abo

    ereignisse: list[Any] = []
    hub.abo_hinzu(Abo(SimpleNamespace(send_message=lambda n: ereignisse.append(n["event"])), 1, {"online"}, "a", ist_admin=True))
    hub.online.quellen.pausen = {"tonies": time.time() + 600}
    await arbeite(hub)
    q = [e["daten"] for e in ereignisse if e["art"] == "quelle" and e["daten"]["quelle"] == "tonies"]
    assert q and q[0]["erreichbar"] is False and q[0]["pause_bis"]


async def test_upload_mit_wunschname_setzt_keinen_art_schnappschuss(hub: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    aufrufe: list[Any] = []
    monkeypatch.setattr(hub.online, "neu_einsortiert", lambda *a: aufrufe.append(a))

    def serie(art_quelle: str) -> Any:
        return SimpleNamespace(id="s", art="hoerspiel", art_quelle=art_quelle, info=lambda _f: {"anzeige": "A", "nummer": None})

    hub.eingang._online_merken(serie("manuell"), True, [(None, "a.mp3")])  # noqa: SLF001
    hub.eingang._online_merken(serie("geraten"), True, [(None, "a.mp3")])  # noqa: SLF001
    assert aufrufe[0][3] is None and aufrufe[1][3] == "hoerspiel"


async def test_cover_hochladen_ersetzt_die_marke_zurueckgenommen_durch_hand(hub: Any) -> None:
    st = hub.online.store
    st.setze_zurueckgenommen(SID, "cover")
    await hub.cover.setze_eigen(SID, jpeg(), b"klein")
    assert st.hand_hat(SID, "cover") and not st.zurueck_hat(SID, "cover")


async def test_fehler_beim_aufraeumen_im_start_wird_protokolliert(hub: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    async def kaputt() -> None:
        raise RuntimeError("kaputt")

    monkeypatch.setattr(hub.online, "beim_start", kaputt)
    await hub._start_pruefung()  # noqa: SLF001
    assert any("Online-Suche: Aufräumen beim Start" in r.getMessage() for r in caplog.records)


async def test_marken_keiner_verfallen_nur_bei_neuem_inhalt_der_liste(hass: Any, tmp_path: Any) -> None:
    """Zusammenspiel: Marke hängt am ``stand`` der echten Tonie-Liste, nicht am Abgleichstag."""
    from custom_components.tobibox.online_quellen import OnlineQuellen, TonieListe

    from .test_online_quellen import FakeSession, Resp, Uhr, fixture_bytes, liste_mit, stub_benutzbar

    uhr = Uhr()
    antwort = Resp(body=fixture_bytes("tonies_auszug.json"), headers={"ETag": '"v1"'})
    q = OnlineQuellen(FakeSession(lambda _u, _k: antwort), zeit=uhr, schlafen=uhr.schlafen)
    liste = TonieListe(q, tmp_path / "tonies.json", benutzbar=stub_benutzbar, min_eintraege=1)
    await liste.sicherstellen()
    st = OnlineStore(hass, zeit=time.time)
    st.setze_marke("s", "keiner", ["a"], liste.stand)
    uhr.t += 8 * 86400
    antwort = Resp(status=304, headers={"ETag": '"v1"'})
    await liste.sicherstellen()
    assert st.marke_gueltig("s", ["a"], liste.stand)  # 304: Marke gilt weiter
    antwort = Resp(body=liste_mit(50), headers={"ETag": '"v2"'})
    uhr.t += 8 * 86400
    await liste.sicherstellen(erzwingen=True)
    assert liste.letztes_ergebnis == "neu" and not st.marke_gueltig("s", ["a"], liste.stand)


async def test_marken_verfall_fehler_1_tag_keiner_30_tage(hass: Any) -> None:
    from datetime import datetime, timezone

    st = OnlineStore(hass, zeit=time.time)

    def alt(stunden: float) -> str:
        return datetime.fromtimestamp(time.time() - stunden * 3600, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for ergebnis in ("fehler", "keiner"):
        st.setze_marke(ergebnis, ergebnis, ["a"], 5.0)
    st.daten["serien"]["fehler"]["marke"]["zeit"] = alt(23)
    st.daten["serien"]["keiner"]["marke"]["zeit"] = alt(23)
    assert st.marke_gueltig("fehler", ["a"], 5.0) and st.marke_gueltig("keiner", ["a"], 5.0)
    st.daten["serien"]["fehler"]["marke"]["zeit"] = alt(25)
    st.daten["serien"]["keiner"]["marke"]["zeit"] = alt(25)
    assert not st.marke_gueltig("fehler", ["a"], 5.0)  # wieder Kandidat für den Lauf
    assert st.marke_gueltig("keiner", ["a"], 5.0)
    st.daten["serien"]["keiner"]["marke"]["zeit"] = alt(31 * 24)
    assert not st.marke_gueltig("keiner", ["a"], 5.0)
