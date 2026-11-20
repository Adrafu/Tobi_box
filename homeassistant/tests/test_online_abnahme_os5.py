"""Online-Suche, Abnahme OS5: drei Befunde aus dem echten HA (B1 bis B3), je als roter Test.

B1 (Zahlen eines durch HA-Neustart abgebrochenen Laufs stehen auf 0): bleibt so, kein Test (Entscheidung 20.11.).
B2: Rücknahme nach Umbenennen von Hand: ``folge_titel`` und ``nummer`` werden gemeinsam geprüft (Design 6.4, festgeschrieben).
B3: Claude-Namensvorschlag beim Einsortieren einer neuen Serie (Namensregel 3.4 festgeschrieben, Pause repariert).
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from custom_components.tobibox.const import CONF_ONLINE_KI_ENTITAET
from custom_components.tobibox.online_quellen import QuellePausiert

from .conftest import braucht_ffmpeg
from .test_online_dienst import FALL, FOLGE, SID, FakeListe, FakeQuellen, KiDienst, lege_bibi, setze_option

pytestmark = braucht_ffmpeg

SID2 = "zwei"


@pytest.fixture
async def hub(starte_integration: Any, nas: Any, lege_mp3: Any) -> Any:
    lege_bibi(nas, lege_mp3, gruende=["tags_fehlen"], serie_gruende=["art_geraten"])
    lege_bibi(nas, lege_mp3, gruende=["tags_fehlen"], serie_gruende=["art_geraten"], name="Ganz Anderes", ordner="anderes", serie_id=SID2)
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    return h


# --------------------------------------------------------------------------
# B2
# --------------------------------------------------------------------------


async def test_b2_ruecknahme_titel_und_nummer_bleiben_gemeinsam_wenn_der_titel_von_hand_geaendert_wurde(hub: Any, nas: Any, lege_mp3: Any) -> None:
    """Design 6.4: ``folge_titel`` und ``nummer`` werden gemeinsam geprüft (``_eine_aenderung_zuruecknehmen``, ``paare``). Entscheidung 20.11.: Design bleibt.
    Titel von Hand geändert: Titel und Nummer bleiben, beide ``seitdem_geaendert``."""
    online = hub.online
    # Zustand nach „Übernehmen“ von Hand (Nr. 59): Titel mit „Folge 177: “, Nummer 177
    stand = hub.medien.serien[SID].serie.stand
    await hub.medien.folge_umbenennen(SID, FOLGE, "Folge 177: Die Spur der Wölfin", stand)
    info = hub.medien.serien[SID]
    serie = info.serie
    serie.setze_info(FOLGE, nummer=177)
    from custom_components.tobibox.media import schreibe_serie  # noqa: PLC0415

    pfad = nas.medien / "bibi"
    schreibe_serie(pfad, serie)
    await hub.medien._aktualisiere_cache(serie, pfad.name)
    online.store.serie(SID).setdefault("aenderungen", []).append(
        {
            "id": "a1",
            "status": "fertig",
            "wer": "hand",
            "zeit": "2026-11-20T10:00:00Z",
            "felder": {
                f"folge_titel@{FOLGE}": {"vorher": FALL["folge"], "nachher": "Folge 177: Die Spur der Wölfin"},
                f"nummer@{FOLGE}": {"vorher": None, "nachher": 177},
            },
        }
    )
    online.store.setze_hand(SID, f"folge_titel@{FOLGE}")
    online.store.setze_hand(SID, f"nummer@{FOLGE}")
    # Schritt 5: Folge von Hand umbenannt, Nummer nicht angefasst
    await hub.medien.folge_umbenennen(SID, FOLGE, "Folge 177: Die Spur der Wölfin (von Hand)", hub.medien.serien[SID].serie.stand)
    assert hub.medien.serien[SID].serie.info(FOLGE).get("nummer") == 177
    erg = await online.zuruecknehmen(SID)
    assert sorted((u["feld"], u["grund"]) for u in erg["uebersprungen"]) == sorted(
        [(f"folge_titel@{FOLGE}", "seitdem_geaendert"), (f"nummer@{FOLGE}", "seitdem_geaendert")]
    ), erg
    assert erg["zurueckgenommen"] == 0
    assert hub.medien.serien[SID].serie.info(FOLGE).get("nummer") == 177


# --------------------------------------------------------------------------
# B3
# --------------------------------------------------------------------------

NAME = "Studio Sonnenhof"
TITEL = "Tafiti und die Reise ans Ende der Welt"


@pytest.fixture
async def hub_sonnenhof(starte_integration: Any, nas: Any, lege_mp3: Any, hass: Any) -> Any:
    """Neue Serie wie nach dem Upload: Name aus dem Interpreten (``serie_aus_interpret``), eine Folge mit dem Titel des Albums."""
    for i in range(1, 4):
        lege_mp3(nas.medien / "sonnenhof" / "f1" / f"{i:02d}.mp3")
    nas.serie("sonnenhof", serie_id="sonne", name=NAME, folgen=["f1"], art="hoerspiel", art_quelle="geraten",
              folgen_info={"f1": {"anzeige": TITEL, "pruefen": True, "pruefen_gruende": ["serie_aus_interpret"]}})
    h = await starte_integration()
    h.online.quellen = FakeQuellen()
    h.online.tonie_liste = FakeListe()
    h.online.ki.drossel._abstand = 0
    return h


async def _neu_einsortiert_arbeiten(hub: Any) -> None:
    hub.online.neu_einsortiert("sonne", True, {"f1": {"anzeige": TITEL, "nummer": None}}, "hoerspiel")
    await hub.online.warte_auf_ende()


async def test_b3_kontrolle_claude_wird_beim_neu_einsortierten_eintrag_gefragt(hub_sonnenhof: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Kontrolle (grün erwartet): Option gesetzt, Quellen gehen: ``neu_einsortiert`` -> Schlange -> Claude wird gefragt."""
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": NAME, "grund": "g"})
    setze_option(hub_sonnenhof, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await _neu_einsortiert_arbeiten(hub_sonnenhof)
    assert len(ki.aufrufe) == 1


async def test_b3_apple_pause_ueberspringt_claude_nicht(hub_sonnenhof: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Hypothese 1: Apple ist pausiert (nach dem Lauf mit 340 Einträgen). ``_arbeite_serie`` kehrt bei ``QuellePausiert`` vor dem Claude-Schritt zurück
    (online.py, ``erg['pause']``-Rückgabe); beim Einsortieren steht nur eine Info im Protokoll. Claude braucht aber nur den Ordner, den Namen
    und die Folgentitel: Die Frage sollte trotzdem gehen."""
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": NAME, "grund": "g"})
    setze_option(hub_sonnenhof, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    hub_sonnenhof.online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    await _neu_einsortiert_arbeiten(hub_sonnenhof)
    assert len(ki.aufrufe) == 1


async def test_b3_name_nur_aus_dem_titel_wird_still_verworfen(hub_sonnenhof: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Namensregel (Design 3.4, Entscheidung 20.11.): Claude antwortet „Tafiti“, das steht nur als Teil des Folgentitels in der Eingabe, nicht als Kandidat,
    Ordner oder heutiger Name. ``pruefe_antwort`` verwirft (``name_nicht_in_eingabe``): Marke ``behalten``, kein Vorschlag."""
    KiDienst(hass, {"entscheidung": "kandidat", "name": "Tafiti", "grund": "Der Titel nennt die Reihe."})
    setze_option(hub_sonnenhof, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    await _neu_einsortiert_arbeiten(hub_sonnenhof)
    assert not hub_sonnenhof.online.vorschlaege_gueltig("sonne")
    assert hub_sonnenhof.online.store.claude_marke("sonne")["ergebnis"] == "behalten"


async def test_b3_pause_keine_doppelte_anfrage_an_claude(hub_sonnenhof: Any, hass: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    """Apple pausiert: Claude wird gefragt (Marke ``behalten``/``vorschlag``). Ein zweiter Durchlauf derselben Serie fragt nicht noch einmal."""
    ki = KiDienst(hass, {"entscheidung": "kandidat", "name": NAME, "grund": "g"})
    setze_option(hub_sonnenhof, monkeypatch, **{CONF_ONLINE_KI_ENTITAET: "ai_task.test_claude"})
    online = hub_sonnenhof.online
    online.quellen.itunes_pause = QuellePausiert("itunes", time.time() + 900)
    await _neu_einsortiert_arbeiten(hub_sonnenhof)
    assert len(ki.aufrufe) == 1
    assert online.store.claude_gueltig("sonne", True)
    erg = await online._arbeite_serie("sonne", folgen=None, neu=True, im_lauf=True, lauf_id=None)
    assert erg["pause"] is not None
    assert len(ki.aufrufe) == 1
