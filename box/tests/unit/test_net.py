"""Netz-Klassen ``home``, ``hotspot``, ``offline`` und die Zeitquelle (``net.py``)."""

from __future__ import annotations

import asyncio

import pytest

from tobibox import events as ev
from tobibox import net
from tobibox.config import NetzKonfig
from tobibox.net import Netz, SimNas, SimNtp, SimSsid, Zeitquelle, klassifiziere, parse_nmcli

HEIM = "TestHeim-WLAN"
HOTSPOT = "TestHandy-Hotspot"


def konfig(**kw) -> NetzKonfig:
    return NetzKonfig(**{"quelle": "sim", "heim_ssid": HEIM, "hotspot_ssid": HOTSPOT, **kw})


# --- Regel -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ssid,nas,nas_host,erwartet",
    [
        (HEIM, True, "nas", "home"),
        (HEIM, False, "nas", "offline"),  # Heim-WLAN, aber der NAS (Tailscale) ist nicht da
        (HEIM, False, None, "home"),  # ohne ``nas_host`` genügt die SSID
        (HOTSPOT, False, "nas", "hotspot"),  # im Hotspot wird der NAS nicht verlangt
        (HOTSPOT, True, None, "hotspot"),
        ("FremdesWLAN", True, "nas", "offline"),
        (None, True, "nas", "offline"),
    ],
)
def test_klassifiziere(ssid, nas, nas_host, erwartet):
    assert klassifiziere(ssid, nas, konfig(nas_host=nas_host)) == ev.NetzKlasse(erwartet)


def test_ohne_konfigurierte_ssid_ist_alles_offline():
    k = NetzKonfig(quelle="sim")
    assert klassifiziere(HEIM, True, k) == ev.NetzKlasse("offline")
    assert klassifiziere(None, True, k) == ev.NetzKlasse("offline")


def test_ssid_vergleich_ist_genau():
    assert klassifiziere(HEIM.lower(), True, konfig()) == ev.NetzKlasse("offline")
    assert klassifiziere(HEIM + " ", True, konfig()) == ev.NetzKlasse("offline")


# --- nmcli -------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "ausgabe,erwartet",
    [
        ("no:Nachbar\nyes:TestHeim-WLAN\nno:Cafe\n", "TestHeim-WLAN"),
        ("yes:Name\\:mit\\:Doppelpunkt\n", "Name:mit:Doppelpunkt"),
        ("no:Nachbar\n", None),
        ("", None),
        ("yes:\n", None),  # verstecktes WLAN ohne Namen
        ("kaputt\n", None),
    ],
)
def test_parse_nmcli(ausgabe, erwartet):
    assert parse_nmcli(ausgabe) == erwartet


async def test_nmcli_fehlt_ist_offline(monkeypatch, caplog):
    async def kein_programm(*a, **kw):
        raise FileNotFoundError("nmcli")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", kein_programm)
    assert await net.NmcliSsid().ssid() is None
    assert await net.TimedatectlNtp().synchron() is False


# --- Netz --------------------------------------------------------------------------------------


class Sammler:
    def __init__(self) -> None:
        self.liste: list[ev.Ereignis] = []

    def __call__(self, e: ev.Ereignis) -> None:
        self.liste.append(e)


def mk(**kw):
    k = konfig(**{"nas_host": "nas", **kw})
    ssid, nas, ntp, aus = SimSsid(), SimNas(True), SimNtp(False), Sammler()
    return Netz(k, ssid, nas, ntp, Zeitquelle(), aus), ssid, nas, ntp, aus


async def test_erste_messung_meldet_die_klasse_einmal():
    n, ssid, *_, aus = mk()
    assert await n.pruefe() == [ev.NetzKlasse("offline")]
    assert await n.pruefe() == []  # nichts Neues: kein Ereignis
    assert aus.liste == [ev.NetzKlasse("offline")]


async def test_wechsel_home_hotspot_offline():
    n, ssid, nas, ntp, aus = mk()
    folge = []
    for wlan in (HEIM, HEIM, HOTSPOT, None, HEIM):
        ssid.setze(wlan)
        folge += [e.klasse for e in await n.pruefe() if isinstance(e, ev.NetzKlasse)]
    assert folge == ["home", "hotspot", "offline", "home"]
    assert n.klasse == ev.NetzKlasse("home")


async def test_nas_weg_macht_aus_home_offline_und_zurueck():
    n, ssid, nas, *_ = mk()
    ssid.setze(HEIM)
    assert (await n.pruefe())[0] == ev.NetzKlasse("home")
    nas.wert = False
    assert await n.pruefe() == [ev.NetzKlasse("offline")]
    nas.wert = True
    assert await n.pruefe() == [ev.NetzKlasse("home")]


async def test_nas_wird_nur_im_heim_wlan_gefragt():
    n, ssid, nas, *_ = mk()
    fragen = []

    async def erreichbar():
        fragen.append(1)
        return True

    nas.erreichbar = erreichbar  # type: ignore[method-assign]
    ssid.setze(HOTSPOT)
    await n.pruefe()
    ssid.setze(None)
    await n.pruefe()
    assert fragen == []
    ssid.setze(HEIM)
    await n.pruefe()
    assert fragen == [1]


async def test_aus_konfig_simulation_und_zeit_system():
    n = Netz.aus_konfig(konfig(), ausgabe=Sammler())
    assert isinstance(n._ssid, SimSsid)
    assert n.zeit.quelle == "system" and n.zeit.vertrauenswuerdig  # Mac: Systemuhr gilt
    n2 = Netz.aus_konfig(NetzKonfig(quelle="networkmanager", heim_ssid=HEIM, nas_host="nas"))
    assert isinstance(n2._ssid, net.NmcliSsid) and isinstance(n2._nas, net.TcpNas) and isinstance(n2._ntp, net.TimedatectlNtp)
    assert n2.zeit.quelle == "unbekannt" and not n2.zeit.vertrauenswuerdig


async def test_asynchrone_ausgabe_wird_abgewartet():
    erhalten = []

    async def aus(e):
        await asyncio.sleep(0)
        erhalten.append(e)

    n = Netz(konfig(), SimSsid(HOTSPOT), None, None, None, aus)
    await n.pruefe()
    assert erhalten == [ev.NetzKlasse("hotspot")]


async def test_tcp_nas_erreichbar_und_nicht():
    async def angenommen(r, w):
        w.close()

    server = await asyncio.start_server(angenommen, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        assert await net.TcpNas("127.0.0.1", port, 1.0).erreichbar() is True
    finally:
        server.close()
        await server.wait_closed()
    assert await net.TcpNas("127.0.0.1", port, 1.0).erreichbar() is False  # Port jetzt zu


# --- Zeitquelle --------------------------------------------------------------------------------


def test_zeitquelle_system_gilt_immer():
    z = Zeitquelle(system=True)
    assert (z.quelle, z.vertrauenswuerdig) == ("system", True)
    assert z.ntp(True) is None and z.rtc(False) is None


def test_zeitquelle_ohne_alles_ist_unbekannt_und_unsicher():
    z = Zeitquelle()
    assert (z.quelle, z.vertrauenswuerdig) == ("unbekannt", False)
    assert z.rtc(False) is None and z.ntp(False) is None


def test_zeitquelle_rtc_dann_ntp():
    z = Zeitquelle()
    assert z.rtc(True) == ev.ZeitquelleGeaendert("rtc", True)
    assert z.rtc(True) is None  # keine Änderung, kein Ereignis
    assert z.ntp(True) == ev.ZeitquelleGeaendert("ntp", True)  # NTP gewinnt
    assert z.ntp(False) is None and z.quelle == "ntp"  # bleibt, auch wenn NTP kurz ausfällt


def test_zeitquelle_nur_ntp_ohne_rtc():
    z = Zeitquelle()
    assert z.ntp(True) == ev.ZeitquelleGeaendert("ntp", True)


async def test_netz_meldet_ntp_als_zeitquelle():
    n, ssid, nas, ntp, aus = mk()
    await n.pruefe()
    ntp.wert = True
    assert await n.pruefe() == [ev.ZeitquelleGeaendert("ntp", True)]
    assert await n.pruefe() == []


def test_zeitquelle_setze_fuer_die_simulation():
    z = Zeitquelle()
    assert z.setze("unbekannt", False) is None
    assert z.setze("ntp", True) == ev.ZeitquelleGeaendert("ntp", True)
