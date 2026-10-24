# Layouts

A layout decides what each speaker plays. It's written for positions, so it works for any
setup; `sounar status` shows what it does with yours.

**Positions** are hours on a clock face around your seat: 12 straight ahead, 3 your right, 6
behind you, 9 your left. From the position: **front** speakers are strictly between 9 and 3
through 12; **surround** speakers are from 3 through 6 to 9; a **sub** is marked as one.

Below, M = (L + R)/2 is the centre of the song (vocals, kick, bass) and S = (L − R)/2 is
what differs between left and right (width, reverb, the room of the recording).

## stereo: as wired

Every output plays what it's wired for: left channels get L, right channels R, a mono output
M. Only the sync delays apply. This is the plain "all speakers play the song" setup (the TV and
Movie Night presets).

## spread: the whole song everywhere

Like stereo, with L' = M + w·S and R' = M − w·S. `width` w = 0 plays the same mono song from
every speaker (good when people are all over the room), 1 is full stereo. (Party.)

## room: arranged for your seat

**Bass.** A crossover at `xover` (Linkwitz-Riley, 150 Hz by default) splits M. Every speaker
plays the same low band, delayed so that all of it lands together at your seat: bass gets
stronger instead of smearing. `bass` raises it on every speaker that may be boosted (setup
asks; some speakers limit their own bass and pump if you push them).

**Front speakers share the stereo picture, with the vocals anchored:**

- The **anchor** is the front speaker nearest 12 o'clock. It plays M + c·S on its side
  (c = 10^(−centre/20)); the other front speakers play c·M ± S. So the vocals come mostly from
  the speaker you face, and the others carry the width. `centre` is how much more of the vocals
  the anchor gets.
- A **symmetric pair** (same angle on both sides) has no anchor: left plays M + S = L, right
  M − S = R. The classic stereo picture.
- A **stereo box** among several front speakers plays as one point. A stereo box that's the only
  front speaker (a soundbar) plays its own stereo.
- Power normalisation keeps the centre as loud as in stereo, and trims (from the calibration)
  even the front speakers out at your seat.
- `vocal` lifts the voice band (2.5 kHz, and a little at 900 Hz) in M only: vocals pop without
  making the whole thing brighter.

**Surround speakers play the room:** S only (so vocals don't come from behind), band-limited
to `amb_lo`–`amb_hi`, cut by `dip` around 2.5 kHz so vocal reverb stays in front, and `haas`
ms late, which the ear reads as a bigger room rather than an echo. `fill` sets how loud that
reaches your seat. One surround speaker gets +S; two or more get +S on the left and −S on the
right, which makes them sound wider.

**Subwoofers** play the low band only.

**Only what applies is offered.** Without surround speakers there's no `fill`; without an
anchor there's no `centre`. The panel and `sounar tune` only show values that do something.

**If an output is missing,** room and spread fall back to stereo on what's connected until it's
back.

The exact formulas, with the reasoning, are in [design.md](design.md) section 5; the code is
`sounar/layouts.py`. `tests/test_layouts.py` checks what each example setup's speakers play.
