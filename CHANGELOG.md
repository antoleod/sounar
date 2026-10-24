# Changelog

All notable changes are listed here. Versions follow [Semantic Versioning](https://semver.org).

## 0.1.0 (unreleased)

First public version, grown out of a one-room prototype.

- Speakers are named by where they sit (a clock face around your seat), so any room works:
  stereo pair, pair plus rear, two pairs, left-centre-right, pair with a subwoofer, and more.
- Three layouts (stereo as wired, room, spread) and nine presets, each with its Easy Effects
  preset and a matched song-leveling target. Live fine-tuning, saved per preset.
- `sounar setup` finds the outputs and asks where each speaker sits; `sounar calibrate`
  measures level and distance with the microphone; `sounar sync` re-aligns after a Bluetooth
  reconnect.
- The guard service repairs routing, volumes and filters after reconnects, silently.
- `sounar status --json` (version 1) for widgets; an Omarchy bar panel and menu entries.
- `sounar doctor` for bug reports, with device addresses and names stripped.
- Installer and uninstaller, per user, no sudo.
