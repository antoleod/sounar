import json

import pytest

from fakes import FakeEffects, bt_sink, original_room_system, bt_names
from sounar import core, paths
from sounar.guard import Guard
from sounar.pipewire import Stream
from sounar.presets import load_presets
from sounar.speakers import examples, load_setup
from sounar.state import Measuring, history_append


@pytest.fixture
def ctx(tmp_home):
    pw = original_room_system()
    s = load_setup(examples()["stereo-box-and-twin-right"])
    s.outputs[0].node, s.outputs[1].node = bt_names(pw)
    notes = []
    c = core.Ctx(s, pw, FakeEffects(), load_presets(None), say=lambda *_: None,
                 notify=lambda t, b="", i="": notes.append((t, b)), settle=0)
    c.notes = notes
    core.switch(c, "music-room")
    return c


def guard(ctx):
    return Guard(lambda: ctx, settle=0)


def test_quiet_when_all_is_well(ctx):
    assert guard(ctx).check() == []


def test_restores_default_output(ctx):
    ctx.pw.default = ctx.setup.outputs[0].node
    msgs = guard(ctx).check()
    assert ctx.pw.default == "sounar" and any("default output" in m for m in msgs)


def test_unmutes_feed_and_sets_100(ctx):
    f = ctx.pw.feed_list[1]
    f.mute, f.volume_raw = True, 30000
    msgs = guard(ctx).check()
    assert not f.mute and f.volume_raw == 65536 and len(msgs) == 2


def test_reconnect_restores_volume_and_notifies_sync(ctx):
    node = ctx.setup.outputs[1].node
    vols = {s.name: s.volume_raw for s in ctx.pw.sinks()}
    history_append("calibrate", {"volumes": vols}, {"volumes": vols, "offsets": {}}, "test")
    g = guard(ctx)
    g.check()
    ctx.pw.remove_sink(node)
    g.check()
    ctx.pw.add_sink(bt_sink(2, "Speaker B", volume_raw=20000))
    msgs = g.check()
    assert ctx.pw._sinks[node].volume_raw == vols[node]
    assert any("reconnected" in m for m in msgs)
    assert ctx.notes[-1][0] == "Speaker reconnected" and "sounar sync" in ctx.notes[-1][1]
    assert core.verify(ctx) == []                       # its graph came back too


def test_restores_latency_offset(ctx):
    a = ctx.pw.sinks()[0]
    history_append("calibrate", {}, {"volumes": {}, "offsets": {f"{a.card}:{a.port}": 140000}}, "test")
    a.offset_us = 0
    guard(ctx).check()
    assert ctx.pw._sinks[a.name].offset_us == 140000


def test_restarts_keepalive(ctx):
    ctx.pw.stream_list = []
    msgs = guard(ctx).check()
    assert ("systemctl", "restart", "sounar-keepalive.service") in ctx.pw.calls and msgs


def test_unmutes_left_streams(ctx):
    ctx.pw.stream_list.append(Stream(401, "browser", True, False, "browser", "Video"))
    paths.state_dir().mkdir(parents=True, exist_ok=True)
    (paths.state_dir() / "muted.json").write_text(json.dumps([{"index": 401, "app": "browser"}]))
    msgs = guard(ctx).check()
    assert not ctx.pw.stream_list[-1].mute and any("left muted" in m for m in msgs)


def test_does_nothing_while_measuring(ctx):
    ctx.pw.default = ctx.setup.outputs[0].node
    with Measuring("sync"):
        assert guard(ctx).check() == []
    assert ctx.pw.default != "sounar"


def test_without_setup_does_nothing(tmp_home):
    c = core.Ctx(None, original_room_system(), FakeEffects(), load_presets(None), say=lambda *_: None)
    assert Guard(lambda: c, settle=0).check() == []


def test_same_error_logged_once(tmp_home):
    from sounar import SounarError
    from sounar.state import log  # noqa: F401

    def broken():
        raise SounarError("setup.toml: unknown setting 'postion'")
    g = Guard(broken, settle=0)
    for _ in range(3):
        g.safe_check()
    lines = [ln for ln in (paths.state_dir() / "log").read_text().splitlines() if "postion" in ln]
    assert len(lines) == 1
