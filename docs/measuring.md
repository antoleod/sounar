# Measuring

Sounar measures with a microphone at your seat. A laptop's built-in mic is fine: put the
laptop where you sit. Setup asks which microphone to use when there's more than one.

While it measures, playing media pauses, other apps are muted, the outputs switch to plain
stereo, and one speaker plays at a time. Afterwards everything comes back. Recordings are
deleted after analysis; nothing leaves your computer.

## `sounar calibrate`: once, and after moving a speaker (about a minute)

1. **Timing:** five chirps from every speaker give its arrival time. The difference between
   speakers on the same output is distance, and doesn't change. It's stored as each speaker's
   offset.
2. **Sync:** as below.
3. **Level:** pink noise from every speaker gives its loudness at your seat (200 Hz–5 kHz,
   where loudness is judged and laptop mics are reasonably flat).
4. **Balance:** the output volumes are set so every output is equally loud at your seat.
   Quieter ones go up first and nothing goes above 100 %. The levels are stored after that,
   and every layout's trims come from them.

## `sounar sync`: after a Bluetooth speaker reconnects (about 15 seconds)

Chirps from the front-most speaker of every output, five times. The earlier outputs get a
delay inside their filter graph so all of them arrive together; up to three passes until
they're within 3 ms. Readings that disagree by more than 10 ms (a Bluetooth hiccup) change
nothing.

Speakers on cables keep their delay, so this is only needed for Bluetooth. The guard tells you
when a Bluetooth speaker reconnected.

## By ear

No microphone, or want to fine-tune? `sounar balance <speaker> ±dB` makes that speaker's output
louder or quieter (and keeps the room presets in step), and `sounar nudge <speaker> ±ms` makes
it play later or sooner. If voices sound doubled, the sync is off by a few ms.

## How chirps are found

A matched filter against an exponential chirp (600 Hz–9 kHz, 80 ms) finds each one. Each chirp
gets its own search window (0.55–1.45 s after it was sent), and its onset is the first sample
at half of that chirp's peak, so reflections and stray clicks don't fool it. The code is in
`sounar/measure.py`; `tests/test_measure.py` and `tests/test_calibrate.py` run it on made-up
rooms.
