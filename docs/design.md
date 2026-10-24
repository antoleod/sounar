# Sounar design

Status: approved for version 0.1 (2026-10-24). This document explains how Sounar is built and
why. It is written for contributors; the README is the place to start as a user.

## 1. What Sounar is for

Sounar (sound + arrange) makes several ordinary speakers on a Linux computer play together as
one well-arranged system, and lets you switch the whole arrangement with one command or one
click: how the speakers share the music (the layout), the balance and delays that make them
land together at your seat, and the Easy Effects preset that goes with it. Song leveling is on
in every preset, and switching never interrupts the music.

It grew out of one person's room (a stereo Bluetooth speaker in front, a second Bluetooth
speaker whose two jacks feed a front-right and a rear-right box). Version 0.1 makes that work
for any room:

- **Who:** anyone on Linux with PipeWire and two or more speakers, on any desktop. Omarchy
  users additionally get a bar panel and menu entries.
- **Success:** someone installs it, `sounar setup` finds their speakers and asks where each one
  sits, a one-minute measurement with the computer's microphone balances and aligns them, and
  presets plus the panel work without editing any code.
- **Naming:** speakers are named by where they sit ("Front left", "Rear right"); device names
  and addresses stay in each user's own config and never appear in the project.
- **Contributions:** sharing a setup, a preset or an Easy Effects preset must be a one-file
  change; tests must run without speakers.

### Not in version 0.1

Speakers in another room, automatic room EQ from the measurements, outputs with more than two
channels (5.1 cards), GNOME/KDE/Waybar widgets, a graphical setup wizard, distro packages.
Each becomes a "help wanted" issue.

## 2. Words

| Word | Meaning |
|---|---|
| **Output** | Something PipeWire plays to: a Bluetooth speaker, a USB speaker, HDMI, built-in speakers. One PipeWire sink with one or two channels. |
| **Speaker** | A box in the room at a position. An output holds one speaker (a mono box, or a **stereo box** that plays its own left and right) or two (an output whose left and right channels feed two separate boxes). |
| **Position** | An hour on a clock face around the seat: 12 = straight ahead, 3 = right, 6 = behind, 9 = left. Fractions are allowed (11.5). A speaker can instead be a **subwoofer**. |
| **Zone** | Derived from the position: **front** (strictly between 9 and 3 through 12), **surround** (3 through 6 to 9), or **sub**. |
| **Setup** | The user's speaker map, `~/.config/sounar/setup.toml`, written by `sounar setup`. |
| **Layout** | How the music is shared: `stereo`, `room` or `spread`. |
| **Preset** | A layout, its values, an Easy Effects preset and a leveling target. |
| **Calibration** | Each speaker's level and arrival time at the seat, measured with a microphone. |
| **Sync** | The extra delay each output needs so all outputs land together (Bluetooth links have different, changing delays). |

### Standard names

Names come from the position angle θ = hour × 30°, folded into (−180°, 180°]:

| θ | Name | id |
|---|---|---|
| \|θ\| ≤ 15° | Centre | `centre` |
| 15° < θ < 75° | Front right | `front-right` |
| −75° < θ < −15° | Front left | `front-left` |
| 75° ≤ \|θ\| ≤ 105° | Side right / Side left | `side-right` / `side-left` |
| 105° < \|θ\| < 165° | Rear right / Rear left | `rear-right` / `rear-left` |
| \|θ\| ≥ 165° | Rear centre | `rear-centre` |
| subwoofer | Sub | `sub` |

A second speaker with the same name gets " 2" (`front-left-2`). The id is written into
`setup.toml` when the setup is made, so it stays stable; re-running setup regenerates ids (and
a moved speaker needs a new calibration anyway). A user may add a `nickname`, shown in the
panel and status; nicknames never leave the machine (`sounar doctor` strips them).

## 3. Files

| File | What |
|---|---|
| `~/.config/sounar/setup.toml` | the speaker map (outputs, speakers, positions, correction EQ, mic, options) |
| `~/.config/sounar/presets.toml` | optional: the user's own presets and overrides of built-in ones |
| `~/.local/state/sounar/state.json` | active and previous preset, fine-tuning, calibration, sync |
| `~/.local/state/sounar/current` | the active preset id (plain text, for menus) |
| `~/.local/state/sounar/history.jsonl` | every volume / latency-offset change with before/after (for `undo` and the guard) |
| `~/.local/state/sounar/log` | one line per change |
| `~/.cache/sounar/` | test recordings, deleted after analysis |
| `~/.local/share/sounar/` | the installed program and its data |
| `~/.config/pipewire/pipewire.conf.d/sounar.conf` | the combined "Sounar" output (written by setup) |
| `~/.config/wireplumber/wireplumber.conf.d/sounar-correction.conf` | correction EQ applied the moment a speaker connects (only when a setup has correction EQ) |

### setup.toml

```toml
# Written by `sounar setup`. Positions are hours on a clock face around your seat:
# 12 = straight ahead, 3 = your right, 6 = behind you, 9 = your left.
version = 1
mic = ""                      # PipeWire source to measure with; empty = the default input

[combine]
node = "sounar"               # the combined output every app plays to
managed = true                # Sounar wrote pipewire.conf.d/sounar.conf for it

[options]
menu = "auto"                 # auto, omarchy, walker, fuzzel, rofi, wofi, bemenu, dmenu, terminal
notify = true

[[output]]
node = "bluez_output.XX_XX_XX_XX_XX_XX.1"   # PipeWire node.name (this machine only)
correction = [                              # optional, applied last, per channel
  { type = "highpass", freq = 50, q = 0.707 },
  { type = "peaking", freq = 85, gain = 4.0, q = 1.2 },
]

  [[output.speaker]]
  id = "front-left"
  channels = ["FL", "FR"]       # both channels = a stereo box
  at = 11
  bass_boost = false            # this speaker protects its own bass; never boost it
  nickname = "Bookshelf"        # optional, local only
```

Example setups in `setups/` use the same format with `node = ""`; `sounar setup --example
<name>` pre-fills the positions and only asks which output is which.

### presets.toml

Built-in presets ship in `sounar/data/presets.toml`. The user file adds presets or overrides
fields of built-in ones by id (`[club] ee = "My EQ"`), and `hidden = true` hides one. The order
of the built-in file, then new user presets, is the menu order.

```toml
[music-room]
label = "Music Room"
tagline = "Vocals up front, full bass, the room filled around you"
icon = "󰝚"                 # a Nerd Font glyph (panel, menus)
layout = "room"
centre = 6
fill = -9
ee = "Sounar Room"
```

## 4. Architecture

The program is a Python package (`sounar/`, Python 3.11+, NumPy) behind one command,
`sounar`. Everything that changes the sound goes through PipeWire's command-line tools
(`pw-dump`, `pw-cli`, `pactl`, `pw-play`, `pw-record`), wrapped in one adapter so tests and
dry runs can replace it.

| Module | Does | Depends on |
|---|---|---|
| `paths` | XDG locations; `SOUNAR_*` environment overrides for tests and dry runs | – |
| `speakers` | the setup model: outputs, speakers, positions, zones, names; read/write `setup.toml` | paths |
| `presets` | built-in + user presets, parameter table (limits, labels, steps, hints), applicability | paths |
| `state` | `state.json`, fine-tuning, calibration, sync, history, the change lock | paths |
| `graph` | builds a PipeWire filter-graph string and records its control values | – |
| `layouts` | **the engine**: setup + preset + calibration + sync → one graph per output; loudness model | graph, speakers, presets |
| `pipewire` | the adapter: sinks, node ids, set/read graphs, volumes, feeds, mutes, default sink, config files; dry-run mode | – |
| `effects` | Easy Effects: preset list, load, bypass, leveling, live leveling target (socket) | pipewire |
| `measure` | test signals, play + record with one speaker at a time, detection maths, pausing players | pipewire |
| `core` | switch, tune, reset, effects choice, balance, nudge, apply, verify, repair | all of the above |
| `calibrate` | `sync` and `calibrate` procedures | measure, core |
| `guard` | the background repair service | core, pipewire |
| `desktop` | notifications, `sounar menu` launchers, Omarchy menu rows | presets, state |
| `status` | text status and `status --json` (versioned contract) | core |
| `wizard` | `sounar setup` | speakers, pipewire, measure |
| `doctor` | anonymised diagnostics for bug reports | everything, read-only |
| `cli` | argument parsing and messages | everything |

The engine (`layouts`, `graph`) is pure: it never calls PipeWire, so it can be tested
exhaustively.

### How sound flows

```
apps ─▶ Easy Effects (taste layer, leveling) ─▶ "Sounar" combined output
            ─▶ one feed per output ─▶ output's filter graph (layout, trims, delays, correction) ─▶ speaker(s)
```

The per-output filter graph is PipeWire's `audioconvert.filter-graph.0` property (PipeWire
1.4.0 or newer), set live with `pw-cli set-param <node> Props`. Changing it does not restart
the Bluetooth stream, so preset switches are silent and delays are sample-exact. A signature in
an unused mixer gain identifies the exact graph, so `verify` can tell a stale graph from the
right one by reading the node's controls back.

## 5. Layouts

Every layout gets the stereo input L, R per output. M = (L + R)/2 and S = (L − R)/2. Each
speaker's chain ends with its delay, then the output's correction EQ.

### stereo ("as wired")

Each output channel plays its own input channel: FL ← L, FR ← R, a mono output ← M. Only sync
delays apply. This is the plain setup: every speaker plays full stereo.

### spread (party)

Like stereo, but with L' = M + w·S and R' = M − w·S (`width` w: 0 = the same mono song
everywhere, 1 = full stereo).

### room

Signals: a Linkwitz-Riley crossover at `xover` splits M into a low band (bass) and a high band;
S is high-passed at the same frequency. The `vocal` presence lift (peaking at 2.5 kHz, Q 0.8,
plus 0.4 × at 900 Hz, Q 1.0) is on the high M band only, so it lifts the centre (vocals)
without touching the sides.

Let c = 10^(−centre/20) and σ = +1 for a speaker left of 12, −1 right, 0 in the Centre zone.

**Front speakers** share the stereo picture, with the vocals anchored in one speaker:

- The **anchor** is the front speaker nearest 12 o'clock. If the nearest ones sit at the same
  angle on opposite sides (a symmetric pair), there is no anchor.
- Anchor: mid weight m = 1, side weight s = σ·c. Others: m = c, s = σ. With no anchor: m = 1,
  s = σ (a plain left/right pair).
- Power normalisation g = √(N / Σ m²), N = number of front speakers, so the centre is as loud
  as in stereo.
- Trims even the front speakers at the seat: trim = clamp(mean front level − own level, ±5 dB).
- A stereo box among several front speakers plays as one point (the same signal on both
  channels). A stereo box that is the only front speaker plays its own stereo (M + S on FL,
  M − S on FR, g = 1), like a soundbar.
- Signal: bass·low + g·trim·(m·high_M + s·high_S).

**Surround speakers** (sides and behind) play ambience: S band-limited to `amb_lo`–`amb_hi`
(two high-passes, one low-pass), cut by `dip` around 2.5 kHz (Q 0.6) so vocal reverb doesn't come
from behind, and `haas` ms late so it feels like room, not echo.

- Gain: g · 10^(fill/20) · 10^((mean front level − own level)/20) / √(number of surround
  speakers), the level-compensation term clamped to ±10 dB. `fill` is how loud the ambience
  reaches the seat relative to the front.
- Polarity: a lone surround speaker gets +S; with two or more, left ones get +S and right ones
  −S, which decorrelates them.
- Signal: bass·low + gain·ambience.

**Subwoofers** play bass·low only.

**Bass:** every speaker plays the same mono low band, so all bass lands together. `bass`
(dB) applies to every speaker with `bass_boost = true` (the default); speakers marked
`bass_boost = false` keep the low band at 0 dB.

**Delays:** each speaker waits for the farthest one: delay = sync(output) + (t_max − t), where t
is the speaker's calibrated arrival offset (0 for each output's reference speaker) and t_max is
the largest offset among the playing speakers. The ambience gets `haas` on top.

**Which values apply:** the panel and `tune` only offer values that do something on this setup:

| Value | Applies when |
|---|---|
| `centre` | there is an anchor and at least one other front speaker |
| `fill`, `haas`, `dip`, `amb_lo`, `amb_hi` | there is at least one surround speaker |
| `bass` | at least one speaker has `bass_boost = true` |
| `vocal`, `xover` | always (room) |
| `width` | spread |

**When speakers are missing:** room and spread need every output of the setup to be
connected. Otherwise the connected outputs play stereo until the rest come back, and the status
says so.

### Your sound stays the same

The original setup is `setups/stereo-box-and-twin-right.toml`: a stereo box at 11 o'clock
(`bass_boost = false`), and a second output whose FL feeds a speaker at 2 and whose FR feeds one
at 4. With the formulas above it gives exactly the original matrix (the anchor is the stereo box
at 11: M + c·S; front right: c·M − S; the lone surround speaker gets +S with the original fill
gain; bass boost on the second output only). A test checks this by simulating the original
graphs and the new ones (section 10).

## 6. Measuring and sync

Measuring needs a microphone at the seat (the laptop's own is fine; `mic` in setup.toml picks
another). Without one, everything works by ear (`sounar balance`, `sounar nudge`).

While measuring, playing media players are paused over MPRIS, every other app stream is
muted (and noted in `muted.json` so the guard can unmute after a crash), the outputs switch to
the stereo layout with the current sync, and afterwards the active preset, the mutes and the
players are restored. One speaker plays at a time: its output's combined feed is soloed (the
others muted) and the test track carries the signal only on the channels that feed that
speaker. Recordings stay in `~/.cache/sounar` and are deleted after analysis.

- **Sync** (`sounar sync`, about 15 s, after a Bluetooth reconnect): chirps from each output's
  reference speaker (its front-most), five times. Each output's arrival includes its current
  sync delay, so the new delays are sync' = (sync − arrival) − min over outputs, which delays
  only the earlier links. Up to three passes until within 3 ms. Readings that disagree by more
  than 10 ms change nothing.
- **Calibrate** (`sounar calibrate`, about a minute, once and after moving a speaker): chirps
  from every speaker give the arrival offset of each speaker against its output's reference
  (distance differences, stable). Then sync as above. Then pink noise from every speaker gives
  its level (200 Hz–5 kHz). The output volumes are set so every output is equally loud at the
  seat (quieter ones go up first, nothing above 100 %), and the levels are stored after that
  change.
- **Detection:** a matched filter against an exponential chirp (600 Hz–9 kHz, 80 ms); each
  chirp has its own search window (0.55–1.45 s after it was sent), and the onset is the first
  sample at half of that chirp's peak, so reflections and stray clicks don't fool it.
- Sync uses only filter-graph delays. PipeWire port latency offsets are left as they are; the
  guard restores the last recorded ones if something resets them.
- **Balance by hand:** `sounar balance <speaker> ±dB` makes that speaker's output louder or
  quieter (raising it towards 100 % first, then lowering the others), and moves the calibrated
  levels with it so room presets stay balanced. **Sync by ear:** `sounar nudge <speaker> ±ms`
  makes that output play later or sooner.

### Keep-alive and the guard

Bluetooth links pick a new delay whenever their stream stops, so `sounar-keepalive.service`
plays silence into the combined output whenever the setup has a Bluetooth output.

`sounar guard` (`sounar-guard.service`) checks every 5 s and right after device events. It
plays no sound and never measures. It repairs:

- the default output: if a reconnecting speaker became the default, it puts "Sounar" back
- Easy Effects: playing into the combined output, and running (when installed)
- the combined output's feeds: unmuted, at 100 %
- after a reconnect: the output's volume and latency offset from the history
- every output runs the active preset's graph, and Easy Effects' leveling target matches
- streams left muted by an interrupted measurement
- the keep-alive stream

After a Bluetooth reconnect it sends one notification: the delay may have shifted, run
`sounar sync` when convenient.

## 7. Easy Effects

Recommended, not required. Without it presets still switch layout, balance and delay. Shipped
presets are prefixed so they never overwrite anyone's own: Sounar Default, Sounar Room,
Sounar Classical, Sounar Classical Room, Sounar Late Night, Sounar Movie Night.

- Each Sounar preset names its Easy Effects preset; `sounar effects <name>` picks another one
  for the active preset (saved as fine-tuning) and `sounar effects preset` goes back.
- `sounar effects off|on` is Easy Effects' global bypass (the correction EQ stays on).
- `sounar effects leveling on|off` flips Autogain in the Easy Effects presets Sounar uses.
- **Loudness matching:** layouts change loudness (the room layout spreads energy differently
  than stereo). A loudness model, from the calibrated levels and the layout gains, estimates
  each preset's loudness against stereo with Sounar Default; the Autogain target is lowered or
  raised by that amount (never above −10 LUFS) through Easy Effects' local socket, so presets
  sound equally loud. Needs Easy Effects 8 (the socket); with older versions presets load but
  the target isn't adjusted.
- Presets live in `~/.local/share/easyeffects/output/` (the installer also handles
  `~/.config/easyeffects/output/` and the Flatpak location).

## 8. Command line and desktop

```
sounar                        status
sounar list                   presets
sounar <preset> | set <preset>, next, prev, back
sounar menu                   preset picker
sounar <value> [+N|-N|=N]     fine-tune the active preset (vocal, bass, centre, fill, ...)
sounar tune vocal=1.5 bass=2  several at once; `sounar reset` undoes fine-tuning
sounar effects ...            see section 7
sounar balance <speaker> ±dB  / sounar nudge <speaker> ±ms
sounar sync | calibrate
sounar setup [--example NAME] / sounar speakers
sounar status --json          the panel's data (docs/status-json.md)
sounar doctor                 anonymised report for bug reports
sounar guard run|check|status
sounar undo | history
sounar apply | verify
sounar uninstall
sounar -q <command>           no notification
SOUNAR_DRY_RUN=1 sounar ...   print every change instead of making it
```

- **Notifications:** `notify-send`, replacing the previous Sounar notification.
- **Menu:** `sounar menu` uses the Omarchy menu when present, else the first of Walker,
  Fuzzel, Rofi, Wofi, bemenu, dmenu, else a numbered list in the terminal.
- **status --json** is a documented, versioned contract (`"version": 1`) so anyone can build a
  widget; adding fields is not a breaking change, renaming or removing is.
- **Omarchy extras** (installed only when Omarchy is detected): the bar panel (plugin
  `sounar.panel`: presets, applicable sliders, Easy Effects choice, leveling and effects
  switches, per-output balance and sync by ear, sync and calibrate buttons; shows "run sounar
  setup" until a setup exists) and menu rows (`sounar menu-install`, refreshed when presets
  change). Key bindings are printed by the installer and, on Omarchy, added after asking.

## 9. Installing

`./install.sh` from a clone, per user, no sudo:

1. Checks: Python 3.11+, NumPy, PipeWire 1.4+, WirePlumber, pipewire-pulse (`pactl`),
   `pw-cli`/`pw-dump`/`pw-play`/`pw-record`, `busctl`; optional Easy Effects, `notify-send`.
2. Copies the package to `~/.local/share/sounar/` and a wrapper to `~/.local/bin/sounar`.
3. Copies the Easy Effects presets (never overwriting a different file with the same name).
4. Installs the user services (`sounar-guard`, `sounar-keepalive`) without enabling them.
5. On Omarchy: installs the panel plugin and offers to add it to the bar and the key bindings.
6. Prints the next step: `sounar setup`.

Nothing changes the sound until `sounar setup` finishes and the user confirms. Setup writes
`setup.toml`, the combined output config, and (if any correction EQ) the WirePlumber rule; it
restarts PipeWire once after asking (music apps such as Spotify may need a restart), makes
"Sounar" the default output, enables the services and offers to calibrate. `git pull &&
./install.sh` updates and keeps config, presets and calibration. `sounar uninstall` (or
`./install.sh --uninstall`) removes the program, services, panel and config files Sounar wrote,
restores the previous default output, and keeps `~/.config/sounar` unless `--purge`.

### Moving the original machine over

`tools/import-prototype.py` reads the prototype's state (calibration, sync, fine-tuning,
presets, the old combined output and correction EQ) into `setup.toml` and `state.json`, keeping
the existing combined output (`managed = false`), so nothing is re-measured and PipeWire needn't
restart. It is run only with the owner's OK, after a dry run.

## 10. Testing

Everything runs in CI without speakers or PipeWire.

- **Graph simulator** (`tests/sim.py`): parses a filter-graph string and runs impulses through
  it (copy, mixer, param_eq biquads, delay). Two graphs are equivalent when every
  input→output impulse response matches.
- **Original sound:** the original program's graphs for every preset, recorded from the
  machine it runs on (`tests/fixtures/prototype/`), must be equivalent to the new engine's
  graphs for the original example setup with the same calibration and sync. Its leveling
  targets must match too.
- **Layouts:** for every example setup, behaviour checks: a symmetric pair reproduces L and R
  above the crossover; surround speakers get only band-limited, delayed side signal; a centre
  speaker gets M; a sub gets only low band; fallbacks when outputs are missing.
- **Measurement maths:** synthetic recordings (a chirp delayed, attenuated and buried in
  noise; pink noise at known levels) must be detected at the right time and level.
- **Fake PipeWire:** anonymised `pw-dump`/`pactl` snapshots stand in for a system; switching,
  tuning, balance, verify, guard repairs and `status --json` are tested against the commands they
  would issue.
- **Setup:** scripted answers produce the expected `setup.toml`.
- CI runs ruff, pytest on Python 3.11–3.13, shellcheck for the scripts, and `qmllint` when
  available.
- On real speakers, a dry run is compared with what is live before anything is switched.

## 11. Repository and contributing

- GitHub `zane8n/sounar`, MIT licence, public history starting clean.
- README: what it does, a panel screenshot, a five-minute quick start, the example setups with
  diagrams, links into `docs/`.
- `CONTRIBUTING.md` (tests, code map, adding a setup or preset), Contributor Covenant code of
  conduct, `SECURITY.md`, `CHANGELOG.md` (version 0.1.0).
- Issue forms: bug report (asks for `sounar doctor`), share your setup, idea; a pull request
  checklist; Discussions with Q&A and Show your setup; labels good first issue, help wanted,
  setup, preset, desktop; starter issues for the items in "Not in version 0.1".
- `docs/`: how it works, layouts, measuring, presets, status-json, troubleshooting.

## 12. Risks

- Only Bluetooth outputs have been tested on real speakers; USB, HDMI and built-in outputs use
  the same PipeWire mechanism but need reports.
- Layout formulas beyond the original setup are reasoned, not tuned by ear; presets may need
  community tuning per setup type.
- Easy Effects' socket and preset format change between versions; Sounar degrades to loading
  presets by name.
