"""HTTP-API der Simulations-Oberfläche (AP 4.9) gegen einen Fake-Socket statt ``sim.sock`` des Dienstes."""

from __future__ import annotations

import asyncio
import json

import pytest

from tobibox.gui import server

pytestmark = pytest.mark.asyncio

ANZEIGE = {
    "ok": True,
    "status": {"zustand": "spielt", "serie": {"id": "s1", "name": "Rabe"}, "folge": {"name": "a.mp3", "track": 0}},
    "offen": [{"uid": "04ffeedd", "art": "unbekannt", "zuerst": "z", "zuletzt": "z", "anzahl": 1}],
    "anzeige": {"lautstaerke": 20, "grenze": 50, "figur": None},
    "verdrahtet": {"netz": False},
    "simuliert": None,
}


class FakeSocket:
    """Ein Unix-Socket, der wie ``sim.sock`` JSON-Zeilen annimmt und feste Antworten gibt."""

    def __init__(self, pfad) -> None:
        self.pfad = pfad
        self.empfangen: list[dict] = []
        self.antworten: dict[str, dict] = {"anzeige": ANZEIGE}
        self.standard = {"ok": True}
        self._srv = None

    async def _client(self, r, w):
        while z := await r.readline():
            d = json.loads(z)
            self.empfangen.append(d)
            w.write((json.dumps(self.antworten.get(d["befehl"], self.standard)) + "\n").encode())
            await w.drain()
        w.close()

    async def start(self):
        self._srv = await asyncio.start_unix_server(self._client, str(self.pfad))

    async def stop(self):
        self._srv.close()
        await self._srv.wait_closed()


@pytest.fixture
async def welt(kurz, tmp_path):
    fake = FakeSocket(kurz / "sim.sock")
    await fake.start()
    zustand = tmp_path / "var"
    zustand.mkdir()
    (zustand / "config.json").write_text(json.dumps({
        "schema_version": 1, "revision": 1, "liste_id": "x",
        "zuordnungen": {
            "04a1b2c3": {"ziel": {"typ": "serie", "serie": "s1"}, "name": "Papas Rabe"},
            "04a1b2c4": {"ziel": {"typ": "folge", "serie": "s1", "folge": "a.mp3"}},
            "04dead01": {"ziel": {"typ": "aktion", "aktion": "status"}},
        },
    }))
    log = tmp_path / "tobibox.log"
    log.write_text("\n".join(json.dumps({"zeit": f"t{i}", "ebene": "INFO", "baustein": "app", "ereignis": f"e{i}", "ergebnis": "ok"})
                             for i in range(40)) + "\n")
    ober = server.Oberflaeche(server.unix_frage(kurz / "sim.sock"), zustand, None, log)
    srv = server.Server(ober, "127.0.0.1", 0)
    await srv.start()
    yield srv, fake
    await srv.stop()
    await fake.stop()


async def http(srv, methode, pfad, koerper=None, kopf=None):
    r, w = await asyncio.open_connection("127.0.0.1", srv.port)
    kopf = {"Host": f"127.0.0.1:{srv.port}", **(kopf or {})}
    daten = b"" if koerper is None else (koerper if isinstance(koerper, bytes) else json.dumps(koerper).encode())
    if koerper is not None:
        kopf.setdefault("Content-Type", "application/json")
        kopf["Content-Length"] = str(len(daten))
    text = f"{methode} {pfad} HTTP/1.1\r\n" + "".join(f"{k}: {v}\r\n" for k, v in kopf.items()) + "\r\n"
    w.write(text.encode() + daten)
    await w.drain()
    roh = await asyncio.wait_for(r.read(), 5)
    w.close()
    kopfteil, _, rumpf = roh.partition(b"\r\n\r\n")
    status = int(kopfteil.split()[1])
    return status, kopfteil.decode(), rumpf


async def test_seite_wird_geliefert(welt):
    srv, _ = welt
    status, kopf, rumpf = await http(srv, "GET", "/")
    assert status == 200 and "text/html" in kopf
    text = rumpf.decode()
    assert "Tobi Box" in text and "Ring noch nicht verdrahtet" in text
    assert "http://" not in text.replace("http://www.w3.org/2000/svg", "")  # keine Abhängigkeit aus dem Netz


async def test_anzeige_fasst_dienst_tobies_serien_und_protokoll_zusammen(welt):
    srv, fake = welt
    status, _, rumpf = await http(srv, "GET", "/api/anzeige")
    d = json.loads(rumpf)
    assert status == 200 and d["dienst"] == "laeuft"
    assert d["status"]["serie"]["name"] == "Rabe" and d["offen"][0]["uid"] == "04ffeedd"
    assert d["anzeige"]["ring"] is None  # Feld fehlt im Status: Seite zeigt grauen Ring
    assert d["verdrahtet"] == {"netz": False}
    assert fake.empfangen == [{"befehl": "anzeige"}]
    namen = {t["uid"]: t for t in d["tobies"]}
    assert namen["04a1b2c3"]["name"] == "Papas Rabe" and namen["04a1b2c4"]["name"] is None
    assert namen["04a1b2c4"]["ziel"] == "Serie s1, Folge a.mp3"
    assert namen["04dead01"]["ziel"] == "Status-Karte"
    assert len(d["protokoll"]["zeilen"]) == server.LOG_ZEILEN and d["protokoll"]["zeilen"][-1].endswith("e39 ok")


async def test_ring_aus_dem_status_wird_durchgereicht(welt):
    srv, fake = welt
    ring = {"farben": ["#ff0000"] * 40, "helligkeit": 25}
    fake.antworten["anzeige"] = {**ANZEIGE, "anzeige": {"ring": ring}}
    d = json.loads((await http(srv, "GET", "/api/anzeige"))[2])
    assert d["anzeige"]["ring"] == ring


async def test_dienst_nicht_erreichbar(welt):
    srv, fake = welt
    await fake.stop()
    d = json.loads((await http(srv, "GET", "/api/anzeige"))[2])
    assert d["dienst"] == "nicht_erreichbar" and len(d["tobies"]) == 3
    await fake.start()  # für den Aufräumer


async def test_befehl_wird_unveraendert_weitergereicht(welt):
    srv, fake = welt
    zeile = {"befehl": "tobie_auflegen", "uid": "04a1b2c3"}
    fake.antworten["tobie_auflegen"] = {"ok": True, "uid": "04a1b2c3", "vorgang": "ab12cd34"}
    status, _, rumpf = await http(srv, "POST", "/api/befehl", zeile)
    assert status == 200 and json.loads(rumpf)["vorgang"] == "ab12cd34"
    assert fake.empfangen == [zeile]


async def test_ablehnung_des_dienstes_kommt_als_antwort_an(welt):
    srv, fake = welt
    fake.antworten["strom"] = {"ok": False, "fehler": "noch_nicht_verdrahtet"}
    status, _, rumpf = await http(srv, "POST", "/api/befehl", {"befehl": "strom", "lader": True})
    assert status == 200 and json.loads(rumpf) == {"ok": False, "fehler": "noch_nicht_verdrahtet"}


@pytest.mark.parametrize("zeile", [{"befehl": "card", "uid": "04a1b2c3", "ziel": {}}, {"befehl": "status"}, {"x": 1}, [1]])
async def test_nur_erlaubte_befehle(welt, zeile):
    srv, fake = welt
    status, _, rumpf = await http(srv, "POST", "/api/befehl", zeile)
    assert status == 400 and json.loads(rumpf)["fehler"] == "befehl_nicht_erlaubt"
    assert fake.empfangen == []


async def test_befehl_ohne_dienst(welt):
    srv, fake = welt
    await fake.stop()
    status, _, rumpf = await http(srv, "POST", "/api/befehl", {"befehl": "taste", "taste": "weiter"})
    assert status == 503 and json.loads(rumpf)["fehler"] == "dienst_nicht_erreichbar"
    await fake.start()


async def test_fremder_host_und_fremde_herkunft_werden_abgewiesen(welt):
    srv, fake = welt
    assert (await http(srv, "GET", "/api/anzeige", kopf={"Host": "boese.example"}))[0] == 403
    s, _, _ = await http(srv, "POST", "/api/befehl", {"befehl": "taste", "taste": "weiter"}, {"Origin": "http://boese.example"})
    assert s == 403 and fake.empfangen == []
    s, _, _ = await http(srv, "POST", "/api/befehl", {"befehl": "taste", "taste": "weiter"}, {"Origin": f"http://127.0.0.1:{srv.port}"})
    assert s == 200


async def test_post_verlangt_json_und_begrenzt_den_koerper(welt):
    srv, _ = welt
    assert (await http(srv, "POST", "/api/befehl", b"{}", {"Content-Type": "text/plain"}))[0] == 415
    assert (await http(srv, "POST", "/api/befehl", b"x" * (server.MAX_KOERPER + 1)))[0] == 413
    assert (await http(srv, "POST", "/api/befehl", b"kein json"))[0] == 400


async def test_unbekannter_pfad_und_methode(welt):
    srv, _ = welt
    assert (await http(srv, "GET", "/etc/passwd"))[0] == 404
    assert (await http(srv, "DELETE", "/api/befehl"))[0] == 405


async def test_server_lauscht_nur_auf_localhost(welt):
    srv, _ = welt
    assert [s.getsockname()[0] for s in srv._server.sockets] == ["127.0.0.1"]


def test_befehl_gui_ohne_konfiguration_ist_exit_2(tmp_path, capsys):
    from tobibox import cli

    assert cli.main(["gui", "--config", str(tmp_path / "gibt-es-nicht.toml"), "--kein-browser"]) == 2
