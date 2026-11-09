"""``ffprobe`` gehärtet (Vertrag W, 5.4) und Tag-Schlüssel je Container (11.2), belegt mit Testdateien aus ``ffmpeg``."""

from __future__ import annotations

import subprocess
from unittest.mock import patch

import pytest

from custom_components.tobibox import ffprobe
from custom_components.tobibox.const import FORMAT_JE_ENDUNG

from .conftest import braucht_ffmpeg, erzeuge_audio

pytestmark = braucht_ffmpeg


def test_befehl_ist_gehaertet():
    cmd = ffprobe.baue_ffprobe_befehl("/tmp/-x y.mp3", "MP3")
    assert cmd[0] == "ffprobe"
    assert isinstance(cmd, list)  # Liste von Argumenten, nie über eine Shell
    i = cmd.index("-protocol_whitelist")
    assert cmd[i + 1] == "file"
    assert cmd[cmd.index("-f") + 1] == "mp3"  # erzwungenes Format aus der Endung
    assert cmd[cmd.index("-v") + 1] == "error"
    assert "-show_format" in cmd and "-show_streams" in cmd
    assert cmd[cmd.index("-print_format") + 1] == "json"
    assert cmd[-1] == "file:/tmp/-x y.mp3"  # Pfad als file:<absolut>, ein führendes - ist keine Option


def test_befehl_relativer_pfad_wird_absolut():
    cmd = ffprobe.baue_ffprobe_befehl("relativ/datei.flac", "flac")
    assert cmd[-1].startswith("file:/")
    assert cmd[cmd.index("-f") + 1] == "flac"


@pytest.mark.parametrize("endung", sorted(FORMAT_JE_ENDUNG))
def test_jede_endung_hat_ein_erzwungenes_format(endung):
    cmd = ffprobe.baue_ffprobe_befehl("/tmp/x." + endung, endung)
    assert cmd[cmd.index("-f") + 1] == FORMAT_JE_ENDUNG[endung]


def test_zeit_und_speicherlimit_beim_start():
    with patch("custom_components.tobibox.ffprobe.subprocess.run") as run:
        run.return_value = subprocess.CompletedProcess([], 1, b"", b"")
        ffprobe.probe_datei("/tmp/gibtsnicht.mp3", "mp3")
    kwargs = run.call_args.kwargs
    assert kwargs["timeout"] == 30
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["preexec_fn"] is not None  # RLIMIT_AS 1 GiB (soweit das System es erlaubt)
    assert "-protocol_whitelist" in run.call_args.args[0]


def test_zeitueberschreitung_ist_nicht_lesbar(tmp_path):
    datei = erzeuge_audio(tmp_path / "a.mp3")
    with patch("custom_components.tobibox.ffprobe.subprocess.run", side_effect=subprocess.TimeoutExpired("ffprobe", 30)):
        assert ffprobe.probe_datei(datei).status == ffprobe.NICHT_LESBAR


def test_gueltige_mp3(tmp_path):
    p = ffprobe.probe_datei(erzeuge_audio(tmp_path / "a.mp3", dauer=1.5))
    assert p.status == ffprobe.OK
    assert p.hat_audio
    assert p.codec == "mp3"
    assert p.format_name == "mp3"
    assert 1.0 < p.dauer_s < 2.5


def test_textdatei_mit_audio_endung_ist_das_falsche_format(tmp_path):
    t = tmp_path / "text.mp3"
    t.write_text("Das ist nur Text, kein Audio.\n" * 50)
    assert ffprobe.pruefe_datei(t).ergebnis == "ungueltig"
    assert ffprobe.probe_datei(t).status == ffprobe.FORMAT_NICHT_ERLAUBT


def test_playlist_mit_audio_endung_wird_nicht_geoeffnet(tmp_path):
    pl = tmp_path / "liste.mp3"
    pl.write_text("#EXTM3U\n#EXTINF:1,x\nhttp://127.0.0.1:9/x.mp3\nfile:///etc/passwd\n")
    assert ffprobe.pruefe_datei(pl).ergebnis == "ungueltig"


def test_defekte_binaerdatei_ist_nicht_lesbar_und_kein_formatfehler(tmp_path):
    kaputt = tmp_path / "rauschen.mp3"
    kaputt.write_bytes(bytes(range(256)) * 40)
    p = ffprobe.pruefe_datei(kaputt)
    assert p.ergebnis == "warnung"
    assert p.hinweis == ffprobe.NICHT_LESBAR


def test_kopierschutz_drms(tmp_path):
    datei = erzeuge_audio(tmp_path / "a.m4a")
    echt = ffprobe.probe_datei(datei)
    echt.codec = "drms"
    with patch("custom_components.tobibox.ffprobe.probe_datei", return_value=echt):
        p = ffprobe.pruefe_datei(datei)
    assert (p.ergebnis, p.hinweis) == ("warnung", ffprobe.KOPIERSCHUTZ)


def test_probedekodierung_fehlgeschlagen(tmp_path):
    datei = erzeuge_audio(tmp_path / "a.mp3")
    with patch("custom_components.tobibox.ffprobe.probedekodierung", return_value=False):
        p = ffprobe.pruefe_datei(datei)
    assert (p.ergebnis, p.hinweis) == ("warnung", ffprobe.PROBEDEKODIERUNG)


def test_ffprobe_fehlt(tmp_path):
    datei = erzeuge_audio(tmp_path / "a.mp3")
    with patch("custom_components.tobibox.ffprobe.ffprobe_pfad", return_value=None):
        p = ffprobe.pruefe_datei(datei)
    assert (p.ergebnis, p.hinweis) == ("nicht_moeglich", ffprobe.FFPROBE_FEHLT)


# --- Tag-Schlüssel je Container (Vertrag W, 11.2) ---


def test_tags_mp3_id3(tmp_path):
    datei = erzeuge_audio(
        tmp_path / "a.mp3",
        album="Hörbuch X (CD 1)",
        album_artist="Autor A",
        artist="Sprecher S",
        title="Kapitel 1",
        track="3/12",
        disc="1/2",
        date="2019-03-01",
        series="Die Känguru-Chroniken",
        **{"series-part": "2"},
    )
    t = ffprobe.probe_datei(datei).tags
    assert ffprobe.tag(t, "album") == "Hörbuch X (CD 1)"
    assert ffprobe.tag(t, "album_interpret") == "Autor A"
    assert ffprobe.tag(t, "interpret") == "Sprecher S"
    assert ffprobe.tag(t, "titel") == "Kapitel 1"
    assert ffprobe.tag(t, "track") == "3/12"
    assert ffprobe.tag(t, "disc") == "1/2"
    assert ffprobe.tag(t, "datum") == "2019-03-01"
    assert ffprobe.tag(t, "serien_tag") == "Die Känguru-Chroniken"
    assert ffprobe.tag(t, "nummer_tag") == "2"


def test_tags_mp3_grouping_und_movement(tmp_path):
    """TIT1 heißt in ``ffprobe`` ``grouping``, MVNM/MVIN ``movement_name`` und ``movement``."""
    datei = erzeuge_audio(tmp_path / "a.mp3", grouping="Gruppe G", movement_name="Satzname", movement="4")
    t = ffprobe.probe_datei(datei).tags
    assert t["grouping"] == "Gruppe G"
    assert t["movement_name"] == "Satzname"
    assert ffprobe.tag(t, "serien_tag") == "Satzname"  # movement_name steht vor grouping
    assert ffprobe.tag(t, "nummer_tag") == "4"


def test_tags_m4b_mit_kapiteln_und_serien_tags(tmp_path):
    datei = erzeuge_audio(
        tmp_path / "b.m4b",
        kapitel=["Kapitel 1", "Kapitel 2"],
        album="Und überhaupt",
        album_artist="Marc-Uwe Kling",
        title="Und überhaupt",
        series="Die Känguru-Chroniken",
        **{"series-part": "2"},
    )
    p = ffprobe.probe_datei(datei)
    assert p.status == ffprobe.OK
    assert p.format_name.startswith("mov,mp4")
    assert ffprobe.tag(p.tags, "album") == "Und überhaupt"
    assert ffprobe.tag(p.tags, "serien_tag") == "Die Känguru-Chroniken"
    assert ffprobe.tag(p.tags, "nummer_tag") == "2"


def test_tags_flac(tmp_path):
    datei = erzeuge_audio(tmp_path / "c.flac", album="FLAC Album", albumartist="AA", tracknumber="4", discnumber="2", date="2001-05")
    t = ffprobe.probe_datei(datei).tags
    assert ffprobe.tag(t, "album") == "FLAC Album"
    assert ffprobe.tag(t, "album_interpret") == "AA"
    assert ffprobe.tag(t, "track") == "4"
    assert ffprobe.tag(t, "disc") == "2"
    assert ffprobe.tag(t, "datum") == "2001-05"


def test_tags_ogg_stehen_im_strom(tmp_path):
    datei = erzeuge_audio(tmp_path / "d.ogg", album="Ogg Album", album_artist="AA", track="2")
    p = ffprobe.probe_datei(datei)
    assert p.status == ffprobe.OK
    assert ffprobe.tag(p.tags, "album") == "Ogg Album"  # Tags der Ogg-Datei liegen am Audio-Strom, nicht im Format
    assert ffprobe.tag(p.tags, "track") == "2"


def test_datei_ohne_tags(tmp_path):
    t = ffprobe.probe_datei(erzeuge_audio(tmp_path / "e.mp3")).tags
    assert ffprobe.tag(t, "album") == ""
    assert ffprobe.tag(t, "serien_tag") == ""
    assert ffprobe.tag(t, "track") == ""


def test_format_tags_gelten_vor_strom_tags():
    from custom_components.tobibox.ffprobe import _tags_zusammen

    daten = {
        "format": {"tags": {"Album": "Aus dem Format"}},
        "streams": [{"codec_type": "audio", "tags": {"album": "Aus dem Strom", "ARTIST": "Nur Strom"}}],
    }
    t = _tags_zusammen(daten)
    assert t["album"] == "Aus dem Format"
    assert t["artist"] == "Nur Strom"


def test_wav_hat_keine_tags_und_ist_gueltig(tmp_path):
    p = ffprobe.pruefe_datei(erzeuge_audio(tmp_path / "f.wav"))
    assert p.ergebnis == "ok"
