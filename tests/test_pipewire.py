import json
import subprocess
from pathlib import Path

import pytest

from sounar.pipewire import PipeWire, db_to_raw, pct, raw_to_db

FIX = Path(__file__).parent / "fixtures" / "pactl"
READS = {("pactl", "-f", "json", "list", "sinks"): "sinks.json",
         ("pactl", "-f", "json", "list", "cards"): "cards.json",
         ("pactl", "-f", "json", "list", "sink-inputs"): "sink-inputs.json"}


class Runner:
    """Answers read commands from the fixtures and records everything else."""
    def __init__(self, extra=None):
        self.calls, self.extra = [], extra or {}

    def __call__(self, args, **kw):
        args = tuple(args)
        if args in READS:
            out = (FIX / READS[args]).read_text()
        elif args in self.extra:
            out = self.extra[args]
        else:
            self.calls.append(args)
            out = ""
        return subprocess.CompletedProcess(args, 0, out, "")


def test_parse_sinks_fixture():
    pw = PipeWire(run=Runner())
    bt = [s for s in pw.sinks() if s.name.startswith("bluez_output.")]
    assert [s.description for s in bt] == ["Speaker A", "Speaker B"]
    a = bt[0]
    assert a.channels == ["FL", "FR"] and a.codec == "aptx" and a.bus == "bluetooth"
    assert a.card == "bluez_card.00_00_00_00_00_01" and a.port == "headset-output"
    assert isinstance(a.offset_us, int)
    assert 0 < a.volume_raw <= 65536


def test_bus_kinds():
    kinds = {s.name: s.bus for s in PipeWire(run=Runner()).sinks()}
    assert kinds["alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__HDMI1__sink"] == "hdmi"
    assert kinds["alsa_output.pci-0000_00_1f.3-platform-skl_hda_dsp_generic.HiFi__Speaker__sink"] == "built-in"
    assert kinds["sounar"] == "virtual"


def test_feeds_of_combine():
    feeds = PipeWire(run=Runner()).feeds("sounar")
    assert [f.sink for f in feeds] == ["bluez_output.00_00_00_00_00_01.1", "bluez_output.00_00_00_00_00_02.1"]
    assert all(not f.mute and f.volume_raw == 65536 for f in feeds)


def test_streams_exclude_feeds():
    names = [s.media for s in PipeWire(run=Runner()).streams("sounar")]
    assert names == ["Speaker keep-alive"]


def test_mutations_run_commands():
    r = Runner()
    pw = PipeWire(run=r)
    pw.set_volume("bluez_output.00_00_00_00_00_01.1", 60000)
    pw.set_feed_mute(121146, True)
    pw.set_default_sink("sounar")
    assert r.calls == [("pactl", "set-sink-volume", "bluez_output.00_00_00_00_00_01.1", "60000"),
                       ("pactl", "set-sink-input-mute", "121146", "1"),
                       ("pactl", "set-default-sink", "sounar")]


def test_set_graph_quotes_text():
    r = Runner()
    PipeWire(run=r).set_graph(42, '{ nodes = [ { name = "a" } ] }')
    args = r.calls[0]
    assert args[:4] == ("pw-cli", "set-param", "42", "Props")
    assert args[4] == '{ params = [ "audioconvert.filter-graph.0" "{ nodes = [ { name = \\"a\\" } ] }" ] }'


def test_dry_run_runs_nothing():
    r, said = Runner(), []
    pw = PipeWire(dry_run=True, run=r, say=said.append)
    pw.sinks()
    pw.set_graph(1, "{ }")
    pw.set_volume("x", 1)
    pw.set_port_offset("card", "port", 1000)
    pw.set_default_sink("sounar")
    pw.systemctl("restart", "sounar-keepalive.service")
    assert r.calls == []
    assert len(said) == 5 and all(s.startswith("would: ") for s in said)


def test_node_ids_and_controls():
    dump = [{"id": 7, "type": "PipeWire:Interface:Node", "info": {"props": {"node.name": "a"}, "params": {"Props": [
        {"volume": 1.0}, {"params": ["snr:Gain 8", 0.25, "s0:Gain 1", 1.0]}]}}},
            {"id": 9, "type": "PipeWire:Interface:Node", "info": {"props": {"node.name": "b"}}}]
    r = Runner({("pw-dump", "Node"): json.dumps(dump), ("pw-dump", "7"): json.dumps(dump[:1])})
    pw = PipeWire(run=r)
    assert pw.node_ids({"a", "c"}) == {"a": 7}
    assert pw.live_controls(7) == {"snr:Gain 8": 0.25, "s0:Gain 1": 1.0}


@pytest.mark.parametrize("text,want", [("pipewire\nCompiled with libpipewire 1.6.8\nLinked with libpipewire 1.6.8\n",
                                        (1, 6, 8)), ("pipewire\nCompiled with libpipewire 1.4.0\n", (1, 4, 0)),
                                       ("", (0, 0, 0))])
def test_version_parse(text, want):
    assert PipeWire(run=Runner({("pipewire", "--version"): text})).version() == want


def test_volume_conversions():
    for raw in (65536, 60000, 30000, 1000):
        assert abs(db_to_raw(raw_to_db(raw)) - raw) <= 1
    assert pct(raw_to_db(65536)) == 100
