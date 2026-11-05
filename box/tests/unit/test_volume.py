"""volume: Minimum gewinnt, nie darüber; Rampe linear."""

import pytest

from tobibox import volume
from tobibox.volume import klemmen, rampe, wirksame_grenze


def test_namen_der_grenzen():
    assert (
        volume.GRENZE_GLOBAL,
        volume.GRENZE_LEISE_ZEIT,
        volume.GRENZE_KOPFHOERER,
        volume.GRENZE_GUTE_NACHT,
        volume.GRENZE_AUSBLENDEN,
    ) == ("global", "leise_zeit", "kopfhoerer", "gute_nacht", "ausblenden")


@pytest.mark.parametrize(
    "grenzen, erwartet",
    [
        ({}, 100),
        ({"global": 60}, 60),
        ({"global": 60, "kopfhoerer": 25}, 25),
        ({"global": 60, "kopfhoerer": 25, "leise_zeit": 30, "ausblenden": 10}, 10),
        ({"global": 60, "kopfhoerer": None}, 60),
        ({"kopfhoerer": None}, 100),
        ({"global": 60, "gute_nacht": 0}, 0),
    ],
)
def test_wirksame_grenze_ist_das_minimum(grenzen, erwartet):
    assert wirksame_grenze(grenzen) == erwartet


@pytest.mark.parametrize(
    "wunsch, grenzen, erwartet",
    [
        (80, {"global": 60}, 60),
        (40, {"global": 60}, 40),
        (40, {"global": 60, "kopfhoerer": 25}, 25),
        (40, {}, 40),
        (-5, {"global": 60}, 0),
        (200, {}, 100),
    ],
)
def test_klemmen_nie_ueber_der_grenze(wunsch, grenzen, erwartet):
    assert klemmen(wunsch, grenzen) == erwartet


@pytest.mark.parametrize("wunsch", range(0, 101, 5))
@pytest.mark.parametrize(
    "grenzen",
    [{"global": 60}, {"global": 60, "kopfhoerer": 25}, {"leise_zeit": 33, "ausblenden": 12}, {}],
)
def test_klemmen_ist_nie_ueber_irgendeiner_grenze(wunsch, grenzen):
    wert = klemmen(wunsch, grenzen)
    assert all(wert <= g for g in grenzen.values())
    assert 0 <= wert <= wunsch


@pytest.mark.parametrize(
    "von, nach, jetzt, erwartet",
    [
        (40, 0, 0.0, 40),  # Anfang
        (40, 0, 1.5, 20),  # Mitte
        (40, 0, 3.0, 0),  # Ende
        (40, 0, 9.0, 0),  # danach begrenzt
        (40, 0, -1.0, 40),  # davor begrenzt
        (40, 0, 0.1, 39),  # 38.67 gerundet
        (50, 20, 1.0, 40),
        (0, 30, 1.5, 15),  # auch aufwärts
    ],
)
def test_rampe(von, nach, jetzt, erwartet):
    assert rampe(von, nach, 0.0, 3.0, jetzt) == erwartet


def test_rampe_hat_dreissig_schritte_in_drei_sekunden():
    werte = [rampe(30, 0, 100.0, 3.0, 100.0 + 0.1 * k) for k in range(31)]
    assert werte[0] == 30 and werte[-1] == 0
    assert werte == sorted(werte, reverse=True)
    assert len(set(werte)) == 31  # jeder Schritt ein anderes Prozent


def test_rampe_dauer_null():
    assert rampe(40, 5, 0.0, 0.0, 0.0) == 5
