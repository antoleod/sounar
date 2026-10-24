# Contributing to Sounar

Thanks for helping. Every room is different, so the most useful thing you can share is what
works (or doesn't) with your speakers.

## Ways to help, easiest first

1. **Share your setup.** Open a [Share your setup](https://github.com/zane8n/sounar/issues/new?template=share_setup.yml)
   issue, or add a file to `setups/` (copy the closest example, keep `node = ""`, draw the room
   in the comment, add a line to `setups/README.md`).
2. **Share a preset.** Presets are a few lines of TOML: see [docs/presets.md](docs/presets.md).
   If it should ship with Sounar, add it to `sounar/data/presets.toml` and say what it's for.
3. **Share an Easy Effects preset.** Put it in `sounar/data/easyeffects/` named `Sounar <Name>.json`,
   with Autogain (song leveling) first in the chain like the others.
4. **Report a bug.** The [bug form](https://github.com/zane8n/sounar/issues/new?template=bug_report.yml)
   asks for the output of `sounar doctor`, which strips device addresses and names.
5. **Write code.** Look for [good first issues](https://github.com/zane8n/sounar/labels/good%20first%20issue)
   and [help wanted](https://github.com/zane8n/sounar/labels/help%20wanted). Widgets for other
   desktops only need [`sounar status --json`](docs/status-json.md).

## Running it from a checkout

```sh
python3 -m venv --system-site-packages .venv
.venv/bin/pip install pytest ruff
.venv/bin/pytest -q          # no speakers or PipeWire needed
.venv/bin/ruff check .
```

To try a change on real speakers without installing:

```sh
SOUNAR_DRY_RUN=1 python3 -m sounar status      # prints every change instead of making it
python3 -m sounar set club                      # for real, with your ~/.config/sounar setup
```

## Where things are

| Path | What |
|---|---|
| `sounar/speakers.py` | the speaker map: positions, zones, standard names, `setup.toml` |
| `sounar/presets.py` | presets and the table of tunable values |
| `sounar/layouts.py` | **the engine**: setup + preset → one filter graph per output (pure, no PipeWire) |
| `sounar/graph.py` | builds PipeWire filter-graph strings |
| `sounar/core.py` | switching, tuning, balance, sync by ear, verify, repair |
| `sounar/measure.py`, `calibrate.py` | test signals, detection, `sync` and `calibrate` |
| `sounar/pipewire.py`, `effects.py` | the only modules that talk to PipeWire and Easy Effects |
| `sounar/guard.py` | the background repair service |
| `sounar/status.py`, `doctor.py`, `desktop.py`, `wizard.py`, `cli.py` | status, reports, menus, setup, the command |
| `integrations/omarchy/` | the Omarchy bar panel (QML) |
| `setups/` | example setups |
| `tests/` | `sim.py` simulates filter graphs; `fakes.py` stands in for PipeWire, Easy Effects and a room |

[docs/design.md](docs/design.md) explains the decisions.

## Pull requests

- Keep each pull request about one thing, and add a test that fails without your change.
  Layout changes need a test in `tests/test_layouts.py` that checks what a speaker plays.
- `tests/test_prototype_equivalence.py` pins the sound of the original room. If a change
  alters it on purpose, say so in the pull request.
- Run `pytest` and `ruff check .` before pushing; CI runs them on Python 3.11 to 3.13.
- Plain language in messages and docs: say what the user hears or sees.
- Never commit device addresses, device names or home paths (a test checks for these).

By contributing you agree that your contribution is licensed under the [MIT licence](LICENSE).
