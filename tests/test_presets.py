import pytest

from sounar import SounarError
from sounar.presets import DEFAULTS, PARAMS, applicable, load_presets
from sounar.speakers import Output, Setup, Speaker, examples, load_setup


def test_builtin_order():
    assert list(load_presets(None)) == ["music-room", "vocal", "immersive", "club", "concert", "late-night",
                                        "tv", "movie", "party"]


def test_builtin_values():
    ps = load_presets(None)
    club = ps["club"]
    assert club.layout == "room" and club.ee == "Sounar Room"
    assert club.params["bass"] == 3.0 and club.params["xover"] == 160.0
    assert club.params["amb_hi"] == DEFAULTS["room"]["amb_hi"]
    assert ps["tv"].params == {} and ps["tv"].ee == "Sounar Default"
    assert ps["party"].params == {"width": 0.5}
    assert ps["concert"].ee == "Sounar Classical Room"


def test_user_override_and_hidden(tmp_path):
    f = tmp_path / "presets.toml"
    f.write_text('[club]\nee = "My EQ"\nbass = 4\n[movie]\nhidden = true\n'
                 '[kitchen]\nlabel = "Kitchen"\nlayout = "spread"\nwidth = 0.2\n')
    ps = load_presets(f)
    assert ps["club"].ee == "My EQ" and ps["club"].params["bass"] == 4.0 and ps["club"].params["xover"] == 160.0
    assert "movie" not in ps
    assert list(ps)[-1] == "kitchen" and ps["kitchen"].params == {"width": 0.2}


def test_unknown_key_error(tmp_path):
    f = tmp_path / "presets.toml"
    f.write_text('[club]\nbas = 4\n')
    with pytest.raises(SounarError, match=r"presets\.toml.*club.*bas"):
        load_presets(f)


def test_value_out_of_range(tmp_path):
    f = tmp_path / "presets.toml"
    f.write_text('[club]\nbass = 40\n')
    with pytest.raises(SounarError, match="-6"):
        load_presets(f)


def test_param_table_complete():
    for layout, vals in DEFAULTS.items():
        for k in vals:
            p = PARAMS[k]
            assert p.lo <= vals[k] <= p.hi, (layout, k)


def _ex(name):
    return load_setup(examples()[name])


def test_applicable_stereo_pair_room():
    a = applicable(_ex("stereo-pair"), "room")
    assert "fill" not in a and "centre" not in a
    assert {"vocal", "xover", "bass"} <= set(a)


def test_applicable_original_room():
    assert applicable(_ex("stereo-box-and-twin-right"), "room") == [
        "vocal", "bass", "centre", "fill", "haas", "dip", "xover", "amb_lo", "amb_hi"]


def test_applicable_lcr_has_centre():
    assert "centre" in applicable(_ex("left-centre-right"), "room")


def test_applicable_no_bass_boost():
    s = Setup([Output("a", [Speaker("front-left", ["FL"], 10, bass_boost=False),
                            Speaker("front-right", ["FR"], 2, bass_boost=False)])])
    assert "bass" not in applicable(s, "room")


def test_applicable_spread_and_stereo():
    s = _ex("quad")
    assert applicable(s, "spread") == ["width"]
    assert applicable(s, "stereo") == []
