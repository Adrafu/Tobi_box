"""Teilautomat ``session``: Lernmodus wartet still (Entscheidung H, 07.11.; ``core-interface.md``, 9.8).

Im Zustand ``lernt`` startet ein aufgelegter Tobie nichts. Die Sitzung wartet auf die Zuordnung, auf
``Bestaetigt`` „abgelehnt“ oder auf die Frist ``LERN_ANTWORT_FRIST_S`` (10 s, ``mono``).
"""

from __future__ import annotations

import pytest
from conftest import (
    S1,
    S2,
    UEB,
    UID_NACHT,
    UID_S1,
    UID_S2,
    UID_STATUS,
    UID_UNBEKANNT,
    SitzungsHarnisch,
    abspielen,
    in_zustand,
    mk_konfig,
    ZUORDNUNGEN,
    zeiger_speichern,
)

from tobibox import events as ev
from tobibox import session


def A(uid=UID_UNBEKANNT, v="v2", seq=5):
    return ev.Aufgelegt(uid, "ntag", False, seq, v)


def abgelehnt(uid=UID_UNBEKANNT):
    return ev.Bestaetigt(uid, "abgelehnt", "2026-11-07T10:00:00.000Z", "gelernt")


def konfig_mit(uid, serie="s2"):
    return ev.KonfigGeladen(mk_konfig({**ZUORDNUNGEN, uid: ev.Zuordnung("serie", serie)}, revision=2))


def hat_ton(out, ton=None):
    toene = [o.ton for o in out if isinstance(o, ev.TonSpielen)]
    return bool(toene) if ton is None else ton in toene


def hat_abspielen(out):
    return [o for o in out if isinstance(o, ev.Abspielen)]


def lernt(name="leer", **kw) -> SitzungsHarnisch:
    h = in_zustand(name, **kw)
    h.sende(ev.LernenGeaendert(True))
    return h


def wartet(uid=UID_UNBEKANNT, **kw) -> SitzungsHarnisch:
    h = lernt("leer", **kw)
    h.sende(A(uid))
    assert h.z.lern_wartet_bis is not None
    return h


# --- Beginn des Wartens -------------------------------------------------------------------------


def test_frist_ist_zehn_sekunden():
    assert session.LERN_ANTWORT_FRIST_S == 10.0


def test_unbekannter_tobie_wartet_still_ohne_ton_und_ohne_ueberraschung():
    h = lernt()
    out = h.sende(A(UID_UNBEKANNT))
    assert out == [ev.Melden("unbekannt", UID_UNBEKANNT, None)]  # Melden läuft weiter, sonst nichts
    assert h.modus == "pausiert" and h.z.figur.uid == UID_UNBEKANNT
    assert h.z.lern_wartet_bis == pytest.approx(h.uhr.jetzt().mono + session.LERN_ANTWORT_FRIST_S)


def test_bekannter_tobie_wartet_ebenfalls_und_spielt_nichts():
    h = lernt()
    out = h.sende(A(UID_S1))
    assert out == [] and h.modus == "pausiert" and h.z.figur.uid == UID_S1
    assert h.z.lern_wartet_bis is not None


def test_aktionskarte_wartet_und_loest_keine_aktion_aus():
    h = lernt()
    out = h.sende(A(UID_NACHT))
    assert out == [] and h.z.lern_wartet_bis is not None


def test_gesperrter_tobie_hat_keine_kennung_und_wartet_nicht():
    h = lernt()
    out = h.sende(ev.Gesperrt(5, "v2"))
    assert hat_abspielen(out) and h.modus == "spielt" and h.z.lern_wartet_bis is None


def test_ohne_lernmodus_gilt_das_normale_verhalten():
    h = in_zustand("leer")
    out = h.sende(A(UID_UNBEKANNT))
    assert hat_ton(out, "unbekannt") and hat_abspielen(out) and h.z.lern_wartet_bis is None


def test_laeuft_eine_wiedergabe_wird_erst_pausiert_und_der_zeiger_gespeichert():
    h = lernt("spielt")
    out = h.sende(A(UID_UNBEKANNT))
    assert out == [
        zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        ev.Pausieren("abgehoben"),
        ev.Melden("unbekannt", UID_UNBEKANNT, None),
    ]
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None


def test_wiedermeldung_und_gleiche_kennung_mit_neuer_vorgangs_id_lassen_das_warten_weiterlaufen():
    h = wartet()
    bis = h.z.lern_wartet_bis
    assert h.sende(A(UID_UNBEKANNT, "v2")) == []  # Wiedermeldung
    assert h.sende(A(UID_UNBEKANNT, "v3")) == []  # verlorenes REMOVED (9.4)
    assert h.z.lern_wartet_bis == bis and h.z.figur.vorgang == "v3" and h.modus == "pausiert"


# --- Zuordnung ------------------------------------------------------------------------------------


def test_zuordnung_startet_sofort_das_neue_ziel_ohne_unbekannt_ton():
    h = wartet()
    out = h.sende(konfig_mit(UID_UNBEKANNT, "s2"))
    assert hat_abspielen(out) == [abspielen("s2", "s2", "x.mp3", 0.0, "v2")]
    assert not hat_ton(out) and not any(isinstance(o, ev.Melden) for o in out)
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None and h.z.figur.art == "serie"


def test_zuordnung_einer_folge_startet_die_folge():
    h = wartet()
    k = mk_konfig({**ZUORDNUNGEN, UID_UNBEKANNT: ev.Zuordnung("folge", "s1", "c.mp3")}, revision=2)
    out = h.sende(ev.KonfigGeladen(k))
    assert [a.datei for a in hat_abspielen(out)] == ["c.mp3"] and h.z.ziel == "folge"


def test_neue_zuordnung_fuer_einen_bekannten_tobie_startet_das_neue_ziel():
    h = wartet(UID_S1)
    out = h.sende(konfig_mit(UID_S1, "s2"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"] and h.modus == "spielt"


def test_konfig_ohne_diesen_tobie_laesst_das_warten_weiterlaufen():
    h = wartet()
    out = h.sende(konfig_mit(UID_S2, "s2"))
    assert out == [] and h.modus == "pausiert" and h.z.lern_wartet_bis is not None


def test_zuordnung_unter_stumm_gibt_nur_den_hinweiston():
    h = wartet()
    h.sende(ev.StummBeginnt())
    out = h.sende(konfig_mit(UID_UNBEKANNT, "s2"))
    assert not hat_abspielen(out) and hat_ton(out, "hinweis") and h.modus == "gehalten"


# --- HA lehnt ab -----------------------------------------------------------------------------------


def test_abgelehnt_unbekannt_verhaelt_sich_wie_normales_auflegen_und_meldet_erneut_unbekannt():
    h = wartet(UID_UNBEKANNT)
    out = h.sende(abgelehnt())
    assert hat_ton(out, "unbekannt") and hat_abspielen(out) == [abspielen("ueb", "ueb", "u1.mp3", 0.0, "v2")]
    # die Outbox hat den Eintrag mit dem ``ack`` gelöscht: ohne neue Meldung wäre der Tobie für HA verschwunden
    assert [o for o in out if isinstance(o, ev.Melden)] == [ev.Melden("unbekannt", UID_UNBEKANNT, None)]
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None and h.z.figur.art == "unbekannt"


def test_abgelehnt_bekannt_spielt_sein_ziel_ohne_ton():
    h = wartet(UID_S1)
    out = h.sende(abgelehnt(UID_S1))
    assert hat_abspielen(out) == [abspielen("s1", "s1", "a.mp3", 0.0, "v2")] and not hat_ton(out)
    assert h.modus == "spielt"


def test_abgelehnt_aktionskarte_loest_dann_die_aktion_aus():
    h = wartet(UID_NACHT)
    out = h.sende(abgelehnt(UID_NACHT))
    assert out == [ev.AktionAusgeloest("gute_nacht", "v2")]


@pytest.mark.parametrize(
    "e",
    [
        ev.Bestaetigt(UID_UNBEKANNT, "zugeordnet", "z", "gelernt"),
        ev.Bestaetigt(UID_UNBEKANNT, "neu", "z", "unbekannt"),
        ev.Bestaetigt(UID_UNBEKANNT, "abgelehnt", "z", "unbekannt"),
        ev.Bestaetigt(UID_S2, "abgelehnt", "z", "gelernt"),
    ],
)
def test_andere_bestaetigungen_beenden_das_warten_nicht(e):
    h = wartet()
    assert h.sende(e) == [] and h.modus == "pausiert" and h.z.lern_wartet_bis is not None


def test_abgelehnt_ohne_warten_ist_wirkungslos():
    h = in_zustand("spielt")
    assert h.sende(abgelehnt(UID_S1)) == []
    assert h.modus == "spielt"


def test_abgelehnt_unter_stumm_gibt_den_hinweiston():
    h = wartet()
    h.sende(ev.StummBeginnt())
    out = h.sende(abgelehnt())
    assert not hat_abspielen(out) and hat_ton(out, "hinweis") and h.modus == "gehalten"


# --- Frist 10 s -------------------------------------------------------------------------------------


def test_frist_zehn_sekunden_wirkt_wie_abgelehnt():
    h = wartet()
    assert h.takt(9.8) == []
    assert h.modus == "pausiert"
    out = h.takt(0.4)
    assert hat_ton(out, "unbekannt") and [a.serie_id for a in hat_abspielen(out)] == ["ueb"]
    assert not any(isinstance(o, ev.Melden) for o in out)
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None


def test_frist_bekannter_tobie_spielt_sein_ziel():
    h = wartet(UID_S1)
    out = h.takt(10.2)
    assert [a.serie_id for a in hat_abspielen(out)] == ["s1"] and not hat_ton(out)


def test_frist_laeuft_auf_mono_ein_sprung_der_wanduhr_aendert_nichts():
    h = wartet()
    h.uhr.setze_wall(h.uhr.wall + 3600)
    assert h.takt(5.0) == [] and h.modus == "pausiert"


def test_zuordnung_nach_der_frist_wechselt_wie_bei_liegendem_tobie_punkt_14():
    h = wartet()
    h.takt(10.2)  # Überraschung läuft
    out = h.sende(konfig_mit(UID_UNBEKANNT, "s2"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"]
    assert h.modus == "spielt" and h.z.serie_id == "s2"


# --- Abheben ---------------------------------------------------------------------------------------


def test_abheben_beendet_das_warten_und_nichts_spielt():
    h = wartet()
    assert h.sende(ev.Abgehoben(1, "v2")) == []
    assert h.modus == "pausiert" and h.z.figur is None and h.z.lern_wartet_bis is None
    assert h.takt(12.0) == []  # auch nach der Frist spielt nichts
    assert h.sende(abgelehnt()) == []


# --- Tasten ----------------------------------------------------------------------------------------


@pytest.mark.parametrize("e", [ev.Hauptknopf("kurz"), ev.Weiter(), ev.Zurueck()])
@pytest.mark.parametrize("uid", [UID_UNBEKANNT, UID_S1])
def test_hauptknopf_vor_zurueck_bewirken_nichts(e, uid):
    h = wartet(uid)
    bis = h.z.lern_wartet_bis
    out = h.sende(e)
    assert hat_abspielen(out) == [] and not hat_ton(out)
    assert h.modus == "pausiert" and h.z.lern_wartet_bis == bis


def test_hauptknopf_lang_gehoert_idle_und_bleibt_unberuehrt():
    h = wartet()
    assert h.sende(ev.Hauptknopf("lang")) == []
    assert h.z.lern_wartet_bis is not None


def test_hauptknopf_nach_dem_ende_des_wartens_spielt_wieder_normal():
    h = wartet(UID_S1)
    h.takt(10.2)
    h.sende(ev.Hauptknopf("kurz"))  # pausiert die Wiedergabe
    assert h.modus == "pausiert"
    assert hat_abspielen(h.sende(ev.Hauptknopf("kurz")))


# --- anderer Tobie, Lernmodus aus ------------------------------------------------------------------


def test_anderer_tobie_nach_dem_ende_des_lernmodus_wird_normal_behandelt():
    h = wartet(UID_UNBEKANNT)
    h.sende(ev.LernenGeaendert(False))  # ``learn`` hat nach dem ersten Tobie beendet
    out = h.sende(A(UID_S2, "v3"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"] and not hat_ton(out)
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None


def test_anderer_unbekannter_tobie_nach_dem_lernmodus_spielt_die_ueberraschung():
    h = wartet(UID_S1)
    h.sende(ev.LernenGeaendert(False))
    out = h.sende(A(UID_UNBEKANNT, "v3"))
    assert hat_ton(out, "unbekannt") and [a.serie_id for a in hat_abspielen(out)] == ["ueb"]


# --- Konfiguration im Warten: nur ein anderes Ziel beendet es (Befund 1) --------------------------------


def konfig_rev(zuordnungen, revision=9):
    return ev.KonfigGeladen(mk_konfig(zuordnungen, revision=revision))


def test_konfig_mit_unveraendertem_ziel_beendet_das_warten_eines_bekannten_tobies_nicht():
    h = wartet(UID_S1)
    bis = h.z.lern_wartet_bis
    assert h.sende(konfig_rev(ZUORDNUNGEN)) == []  # fremde Revision, alles gleich
    assert h.modus == "pausiert" and h.z.lern_wartet_bis == bis and h.z.lern_ziel == ZUORDNUNGEN[UID_S1]


def test_konfig_mit_unveraendertem_ziel_laesst_eine_aktionskarte_warten_ohne_aktion():
    h = wartet(UID_NACHT)
    out = h.sende(konfig_rev(ZUORDNUNGEN))
    assert out == [] and h.z.lern_wartet_bis is not None


def test_konfig_mit_anderem_tobie_geaendert_laesst_das_warten_weiterlaufen():
    h = wartet(UID_S1)
    assert h.sende(konfig_mit(UID_S2, "s1")) == []  # UID_S2 bekommt ein anderes Ziel, UID_S1 bleibt
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None
    # die neue Konfiguration gilt trotzdem für die Sitzung
    assert h.z.konfig.zuordnungen[UID_S2] == ev.Zuordnung("serie", "s1")


def test_konfig_nach_gleicher_konfig_mit_neuem_ziel_beendet_das_warten():
    h = wartet(UID_S1)
    h.sende(konfig_rev(ZUORDNUNGEN, 9))
    out = h.sende(konfig_mit(UID_S1, "s2"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"] and h.modus == "spielt"


def test_konfig_ohne_zuordnung_des_wartenden_bekannten_tobies_beendet_das_warten_nicht():
    h = wartet(UID_S1)
    rest = {k: v for k, v in ZUORDNUNGEN.items() if k != UID_S1}
    assert h.sende(konfig_rev(rest)) == [] and h.z.lern_wartet_bis is not None


def test_aktionskarte_mit_anderer_aktion_beendet_das_warten_und_loest_die_neue_aus():
    h = wartet(UID_NACHT)
    out = h.sende(konfig_rev({**ZUORDNUNGEN, UID_NACHT: ev.Zuordnung("aktion", aktion="status")}))
    assert out == [ev.AktionAusgeloest("status", "v2")]


def test_unbekannter_tobie_jedes_neue_ziel_beendet_das_warten():
    h = wartet(UID_UNBEKANNT)
    assert h.z.lern_ziel is None
    out = h.sende(konfig_rev({**ZUORDNUNGEN, UID_UNBEKANNT: ev.Zuordnung("serie", "s2")}))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"]
    h = wartet(UID_UNBEKANNT)
    out = h.sende(konfig_rev({**ZUORDNUNGEN, UID_UNBEKANNT: ev.Zuordnung("aktion", aktion="status")}))
    assert out == [ev.AktionAusgeloest("status", "v2")]


def test_konfig_nach_dem_ende_des_wartens_folgt_punkt_14_wie_immer():
    h = wartet(UID_S1)
    h.takt(10.2)  # altes Ziel läuft
    assert h.z.lern_ziel is None and h.z.lern_wartet_bis is None
    out = h.sende(konfig_mit(UID_S1, "s2"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"]


# --- Aktionskarte und Frist (Befund 5) ------------------------------------------------------------------


@pytest.mark.parametrize("uid,aktion", [(UID_NACHT, "gute_nacht"), (UID_STATUS, "status")])
def test_aktionskarte_loest_nach_der_frist_ihre_aktion_aus(uid, aktion):
    h = wartet(uid)
    assert h.takt(9.8) == []
    out = h.takt(0.4)
    assert out == [ev.AktionAusgeloest(aktion, "v2")]
    assert h.z.lern_wartet_bis is None and h.z.figur.art == "aktion"


# --- Wiedermeldung im Zustand spielt, Zustand unbekannt (Befund 6) -------------------------------------


def test_gleiche_kennung_mit_neuer_vorgangs_id_im_zustand_spielt_wartet_nicht():
    h = lernt("spielt")  # UID_S1 spielt
    out = h.sende(A(UID_S1, "v9"))  # verlorenes REMOVED (9.4)
    assert out == [] and h.modus == "spielt" and h.z.lern_wartet_bis is None
    assert h.z.figur.vorgang == "v9"


def test_warten_im_zustand_unbekannt_pausiert_speichert_den_zeiger_und_wartet():
    h = lernt("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    assert h.modus == "unbekannt"
    out = h.sende(A(UID_UNBEKANNT, "v2"))
    assert out == [
        ev.Pausieren("leser_unbekannt"),
        zeiger_speichern("s1", "a.mp3", 0, 10.0, "figurwechsel"),
        ev.Melden("unbekannt", UID_UNBEKANNT, None),
    ]
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None and h.z.unbekannt_seit is None
    assert not hat_abspielen(h.takt(9.0))
    out = h.takt(1.2)  # die Frist endet wie sonst
    assert hat_ton(out, "unbekannt") and [a.serie_id for a in hat_abspielen(out)] == ["ueb"]


def test_warten_im_zustand_unbekannt_bekannter_tobie_mit_neuer_vorgangs_id_wartet_ebenfalls():
    h = lernt("spielt")
    h.sende(ev.LeserAlarm("kein_herzschlag"))
    out = h.sende(A(UID_S1, "v9"))
    assert ev.Pausieren("leser_unbekannt") in out and not hat_abspielen(out)
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None and h.z.lern_ziel == ZUORDNUNGEN[UID_S1]


# --- Leserausfall im Warten (Befund 8) -----------------------------------------------------------------


def herzschlag(present):
    return ev.LeserHerzschlag(present, 10, 100, 1, 0, 0, 100)


@pytest.mark.parametrize("alarm", [ev.LeserAlarm("kein_herzschlag"), ev.LeserAlarm("getrennt")])
def test_leserausfall_im_warten_aendert_nichts_die_frist_laeuft_weiter(alarm):
    h = wartet(UID_S1)
    bis = h.z.lern_wartet_bis
    assert h.sende(alarm) == []
    assert h.modus == "pausiert" and h.z.lern_wartet_bis == bis and h.z.unbekannt_seit is None
    out = h.takt(10.2)  # das Warten endet wie sonst durch die Frist
    assert [a.serie_id for a in hat_abspielen(out)] == ["s1"]


def test_nach_dem_ausfall_liegt_der_tobie_noch_das_warten_geht_weiter():
    h = wartet(UID_S1)
    h.sende(ev.LeserHallo(1, "1.0", "b", "ok"))
    assert h.sende(herzschlag(True)) == []
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None and h.z.figur.uid == UID_S1


def test_nach_dem_ausfall_ist_der_tobie_weg_das_warten_endet_ohne_wirkung():
    h = wartet(UID_S1)
    h.sende(ev.LeserHallo(1, "1.0", "b", "ok"))
    assert h.sende(herzschlag(False)) == []  # 9.3 „Danach“: wie Abheben
    assert h.modus == "pausiert" and h.z.figur is None and h.z.lern_wartet_bis is None and h.z.lern_ziel is None
    assert h.takt(12.0) == []  # auch nach der Frist spielt nichts


# --- „stumm“ im Warten (Befund 8) ---------------------------------------------------------------------


def test_stumm_beginnt_im_warten_das_warten_geht_weiter_und_endet_mit_hinweiston():
    h = wartet(UID_S1)
    assert h.sende(ev.StummBeginnt()) == [] and h.z.lern_wartet_bis is not None
    out = h.takt(10.2)
    assert not hat_abspielen(out) and hat_ton(out, "hinweis") and h.modus == "gehalten"


def test_stumm_endet_im_warten_aendert_nichts():
    h = lernt()
    h.sende(ev.StummBeginnt())
    h.sende(A(UID_S1))
    assert h.z.lern_wartet_bis is not None and h.modus == "pausiert"
    assert h.sende(ev.StummEndet()) == []
    assert h.modus == "pausiert" and h.z.lern_wartet_bis is not None
    out = h.takt(10.2)
    assert [a.serie_id for a in hat_abspielen(out)] == ["s1"] and not hat_ton(out)


def test_aufgelegt_unter_stumm_wartet_und_endet_mit_zuordnung_als_hinweiston():
    h = lernt()
    h.sende(ev.StummBeginnt())
    assert h.sende(A(UID_UNBEKANNT)) == [ev.Melden("unbekannt", UID_UNBEKANNT, None)]
    out = h.sende(konfig_mit(UID_UNBEKANNT, "s2"))
    assert not hat_abspielen(out) and hat_ton(out, "hinweis") and h.modus == "gehalten"


# --- Gesperrt und anderer Tobie im Warten (Befund 8) --------------------------------------------------


def test_gesperrt_im_warten_beendet_es_und_spielt_wie_ohne_lernmodus_die_ueberraschung():
    h = wartet(UID_S1)
    out = h.sende(ev.Gesperrt(6, "v3"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["ueb"] and not hat_ton(out, "unbekannt")
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None and h.z.figur.uid is None and h.z.figur.art == "gesperrt"
    assert h.z.lern_ziel is None


def test_anderer_tobie_im_warten_ohne_lernmodus_wird_normal_behandelt():
    h = wartet(UID_S1)
    h.sende(ev.LernenGeaendert(False))
    out = h.sende(A(UID_S2, "v3"))
    assert [a.serie_id for a in hat_abspielen(out)] == ["s2"] and not hat_ton(out)
    assert h.modus == "spielt" and h.z.lern_wartet_bis is None and h.z.lern_ziel is None


def test_anderer_tobie_im_warten_mit_laufendem_lernmodus_wartet_neu_mit_eigenem_ziel():
    h = wartet(UID_UNBEKANNT)
    assert h.z.lern_ziel is None
    h.sende(A(UID_S2, "v3"))
    assert h.z.figur.uid == UID_S2 and h.z.lern_wartet_bis is not None and h.z.lern_ziel == ZUORDNUNGEN[UID_S2]
    # eine Konfiguration, die nur den ersten Tobie zuordnet, ändert nichts mehr
    assert h.sende(konfig_mit(UID_UNBEKANNT, "s1")) == [] and h.z.lern_wartet_bis is not None
