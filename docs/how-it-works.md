# How Sounar works

```
apps ─▶ Easy Effects (EQ, widening, song leveling) ─▶ "Sounar" combined output
          ─▶ one feed per output ─▶ the output's filter graph ─▶ its speaker(s)
```

**The combined output.** Setup creates a PipeWire output called "Sounar" (a `combine-stream`
module, in `~/.config/pipewire/pipewire.conf.d/sounar.conf`) that feeds every output in your
setup. Apps play to it like any other output, and your volume keys control it.

**A filter graph per output.** Every output runs a small graph inside PipeWire (the
`audioconvert.filter-graph.0` property, PipeWire 1.4+): mixers, EQs and delays that decide what
each of its speakers plays. Sounar writes these graphs live with `pw-cli`. Changing them
doesn't restart the stream, so a preset switch is silent and the delays are exact to the
sample. The graphs come from the [layout engine](layouts.md), which only needs your speaker
map, the preset and the calibration.

**Calibration and sync.** [Measuring](measuring.md) records each speaker's level and arrival
time at your seat. The levels give each layout its trims, so switching never needs a new
measurement. Sync delays line the outputs up; Bluetooth adds a delay that changes whenever a
speaker reconnects, so `sounar sync` re-measures just that.

**Easy Effects.** Each preset loads an Easy Effects preset. Sounar also moves the song-leveling
(Autogain) target per preset: the room layout spreads sound differently than stereo, and
without that, switching presets would change the loudness.

**The keep-alive.** A Bluetooth link picks a new delay every time its stream stops and starts.
`sounar-keepalive.service` plays silence into the combined output so the streams never stop,
which keeps the sync you measured.

**The guard.** `sounar-guard.service` checks every few seconds, and right after any device
change, that everything is as it should be: the default output, Easy Effects' routing, the
feeds, every output's graph and leveling target, latency offsets, and volumes after a
reconnect. It repairs what it finds silently and never plays a sound. After a Bluetooth
reconnect it sends one notification suggesting `sounar sync`.

**One change at a time.** The panel, keys, menu and guard can all ask for changes at once. A
lock serialises them, and changes wait while a measurement is running.

## Files

| File | What |
|---|---|
| `~/.config/sounar/setup.toml` | your speaker map |
| `~/.config/sounar/presets.toml` | your own presets and changes to the built-in ones |
| `~/.local/state/sounar/` | active preset, fine-tuning, calibration, sync, history, log |
| `~/.local/share/sounar/` | the program |
| `~/.config/pipewire/pipewire.conf.d/sounar.conf` | the combined output |
| `~/.config/wireplumber/wireplumber.conf.d/sounar-correction.conf` | correction EQ applied when a speaker connects (only if your setup has correction EQ) |
| `~/.config/systemd/user/sounar-*.service` | the guard and the keep-alive |
