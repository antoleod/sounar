# Troubleshooting

Start with `sounar status` (what it thinks is playing) and `sounar doctor` (a report you can
paste into an issue). `sounar guard status` shows what the guard repaired recently.

**Voices sound doubled or smeared.** The outputs are out of sync, usually after a Bluetooth
speaker reconnected: `sounar sync`. Fine-tune by ear with `sounar nudge <speaker> ±1`.

**One side is louder.** `sounar calibrate`, or by ear: `sounar balance <speaker> ±0.5`.

**"chirps not heard clearly".** The volume was too low or the room too loud. Turn the
"Sounar" output up to a normal listening level, keep quiet, and try again. Nothing was changed.

**"readings unsteady".** A Bluetooth link hiccupped during the measurement. Try again; nothing
was changed.

**No sound from an app after setup.** Some apps (Spotify especially) keep the output they had
when PipeWire restarted: restart the app. Check that "Sounar" is the default output.

**A speaker is missing.** Room and spread presets play plain stereo on what's connected until it's
back; the guard re-applies everything when it reconnects.

**The panel or `sounar status` says "not applied".** Something replaced an output's filter graph
(usually a reconnect). The guard fixes it within seconds; `sounar apply` does it right away.

**Restarting WirePlumber or PipeWire.** Easy Effects can lose its connection to the "Sounar"
output: restart Easy Effects (the guard does this itself when it sees Easy Effects playing into
a single speaker). Apps may need restarting too (see above).

**Measuring with other sounds playing.** Sounar pauses media players and mutes other apps while it
measures. If a measurement was killed halfway, the guard unmutes them.

**Removing it.** `sounar uninstall` (add `--purge` to also remove your setup and calibration).
Then `systemctl --user restart pipewire pipewire-pulse wireplumber` removes the "Sounar" output.

Still stuck? Open a [bug report](https://github.com/zane8n/sounar/issues/new?template=bug_report.yml)
with the output of `sounar doctor`.
