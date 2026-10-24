import pytest

from fakes import FakeEffects, FakePlayers, FakeRoom, original_room_system, bt_names
from sounar import SounarError, core
from sounar.calibrate import calibrate, new_sync, plan_balance, sync
from sounar.graph import MAX_DELAY
from sounar.presets import load_presets
from sounar.speakers import examples, load_setup
from sounar.state import load_state, save_state


def prototype_set_sync(sa, se, box_late_ms):
    d = sa - se - box_late_ms
    d = max(-(MAX_DELAY * 1000 - 60), min(MAX_DELAY * 1000 - 60, d))
    return {"a": round(max(0.0, d), 1), "e": round(max(0.0, -d), 1)}


@pytest.mark.parametrize("sa,se,gap", [(0, 17.9, 3.2), (0, 17.9, -4.0), (6.2, 0, 10.0), (0, 0, -25.0), (0, 0, 600)])
def test_new_sync_two_outputs_matches_prototype(sa, se, gap):
    assert new_sync({"a": sa, "e": se}, {"a": gap, "e": 0.0}) == prototype_set_sync(sa, se, gap)


def test_new_sync_three_outputs():
    assert new_sync({"a": 0, "b": 0, "c": 0}, {"a": 30.0, "b": 10.0, "c": 20.0}) == {"a": 0.0, "b": 20.0, "c": 10.0}


def test_plan_balance_never_above_100():
    deltas = plan_balance([0.0, -5.0], [0.0, -3.0])
    assert deltas[1] <= 5.0 and deltas[0] <= 0.0
    assert deltas == pytest.approx([0.0, 3.0])
    assert plan_balance([0.0, 0.0], [0.0, -3.0]) == pytest.approx([-3.0, 0.0])
    assert plan_balance([0.0, -20.0], [0.0, -10.0]) == pytest.approx([0.0, 10.0])     # up: limited by headroom
    assert plan_balance([0.0, 0.0], [0.0, -10.0]) == pytest.approx([-6.0, 0.0])      # down: at most 6 dB


def make_ctx(room_kw=None):
    pw = original_room_system()
    s = load_setup(examples()["stereo-box-and-twin-right"])
    names = bt_names(pw)
    s.outputs[0].node, s.outputs[1].node = names
    room = FakeRoom(pw, s, **(room_kw or {}))
    players = FakePlayers()
    c = core.Ctx(s, pw, FakeEffects(), load_presets(None), say=lambda *_: None, notify=lambda *a: None, settle=0,
                 recorder=room, extra={"players": players})
    return c, room, players


ROOM = dict(link_ms={"front-left": 140.0, "front-right": 122.0},
            acoustic_ms={"front-left": 0.0, "front-right": 0.0, "rear-right": 3.0},
            gain_db={"front-left": -6.0, "front-right": -3.0, "rear-right": -3.0})


def test_sync_fake_room(tmp_home):
    ctx, room, players = make_ctx(ROOM)
    core.switch(ctx, "music-room")
    sync(ctx)
    st = load_state(ctx.presets)
    assert st["sync_ms"]["front-left"] == 0.0
    assert st["sync_ms"]["front-right"] == pytest.approx(18.0, abs=0.5)
    assert players.resumed and core.verify(ctx) == []


def test_calibrate_fake_room(tmp_home):
    ctx, room, players = make_ctx(ROOM)
    core.switch(ctx, "music-room")
    calibrate(ctx)
    st = load_state(ctx.presets)
    cal = st["calibration"]
    assert cal["source"] == "sounar calibrate" and cal["ts"]
    assert cal["offsets_ms"]["rear-right"] == pytest.approx(3.0, abs=0.3)
    assert cal["offsets_ms"]["front-right"] == 0.0 and cal["offsets_ms"]["front-left"] == 0.0
    assert st["sync_ms"]["front-right"] == pytest.approx(18.0, abs=0.5)
    bal = core.output_balance_db(ctx, st)
    assert abs(bal["front-left"] - bal["front-right"]) < 1.0         # outputs even at the seat
    assert all(s.volume_raw <= 65536 for s in ctx.pw.sinks())
    assert core.verify(ctx) == []                                    # the preset is back on
    assert all(not f.mute for f in ctx.pw.feeds("sounar"))


def test_noisy_room_changes_nothing(tmp_home):
    ctx, room, players = make_ctx(dict(ROOM, noise=20.0))
    core.switch(ctx, "music-room")
    st0 = load_state(ctx.presets)
    with pytest.raises(SounarError, match="chirps not heard"):
        calibrate(ctx)
    st = load_state(ctx.presets)
    assert st["sync_ms"] == st0["sync_ms"] and st["calibration"] == st0["calibration"]
    assert all(not f.mute for f in ctx.pw.feeds("sounar"))
    assert players.resumed and core.verify(ctx) == []
    assert all(not s.mute for s in ctx.pw.streams())


def test_other_apps_muted_then_restored(tmp_home):
    from sounar.pipewire import Stream
    ctx, room, players = make_ctx(ROOM)
    ctx.pw.stream_list.append(Stream(400, "browser", False, False, "browser", "Video"))
    seen = []
    room.on_play = lambda: seen.append([s.mute for s in ctx.pw.streams() if s.app == "browser"])
    sync(ctx)
    assert seen and seen[0] == [True]
    assert [s.mute for s in ctx.pw.streams() if s.app == "browser"] == [False]


def test_calibrate_needs_every_output(tmp_home):
    ctx, room, players = make_ctx(ROOM)
    ctx.pw.remove_sink(ctx.setup.outputs[1].node)
    with pytest.raises(SounarError, match="connect"):
        calibrate(ctx)


def test_sync_needs_two_outputs(tmp_home):
    ctx, room, players = make_ctx(ROOM)
    ctx.pw.remove_sink(ctx.setup.outputs[1].node)
    with pytest.raises(SounarError, match="two outputs"):
        sync(ctx)


def test_unsteady_readings_change_nothing(tmp_home):
    ctx, room, players = make_ctx(dict(ROOM, jitter_ms=80.0))
    st = load_state(ctx.presets)
    st["sync_ms"] = {"front-left": 0.0, "front-right": 5.0}
    save_state(st)
    with pytest.raises(SounarError, match="unsteady"):
        sync(ctx)
    assert load_state(ctx.presets)["sync_ms"] == {"front-left": 0.0, "front-right": 5.0}
