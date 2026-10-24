#!/usr/bin/env python3
"""Move the Sounar prototype's setup over to Sounar 0.1 without measuring anything again.

    python3 -I tools/import-prototype.py [--dry-run] [--home DIR] [--config DIR] [--state DIR]

The prototype (the one-room version Sounar grew from) kept a stereo box at 11 o'clock and a
second output whose left jack fed a speaker at 2 and whose right jack fed one at 4. This reads
its files and writes:

  setup.toml     the two outputs (from its correction rule, in order), their correction EQ, the
                 microphone, and its existing combined output (kept, so PipeWire needn't restart)
  state.json     active and previous preset, fine-tuning, calibration (levels, the rear speaker's
                 offset) and sync delays, mapped to the new speaker ids
  presets.toml   only what differs from Sounar's built-in presets
  history.jsonl  the last recorded volumes and latency offsets, so the guard keeps restoring them

The prototype's own state.json and presets.toml are copied to <state>/prototype-backup first.
Its files are read by position (its own order), so no device name is needed here.
"""
import argparse
import json
import re
import shutil
import sys
import tomllib
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from sounar.presets import load_presets  # noqa: E402
from sounar.speakers import Output, Setup, Speaker, dumps  # noqa: E402

EE = {"Default": "Sounar Default", "Default Room": "Sounar Room", "Classical Clarity": "Sounar Classical",
      "Classical Room": "Sounar Classical Room", "Late Night": "Sounar Late Night", "Movie Night": "Sounar Movie Night"}
IDS = ["front-left", "front-right", "rear-right"]
RULE = re.compile(r'node\.name\s*=\s*"([^"]+)".*?filters\s*=\s*\[(.*?)\]\s*\}', re.S)
EQ = re.compile(r"\{ type = bq_(\w+) freq = ([-\d.]+) gain = ([-\d.]+) q = ([-\d.]+) \}")


def corrections(home):
    for f in sorted((home / ".config/wireplumber/wireplumber.conf.d").glob("*speaker-correction.conf")):
        rules = RULE.findall(f.read_text())
        if len(rules) == 2:
            return [(node, [{"type": t, "freq": float(fr), "gain": float(g), "q": float(q)}
                            for t, fr, g, q in EQ.findall(filters)]) for node, filters in rules]
    raise SystemExit("couldn't find the prototype's correction rule with two outputs")


def combine_node(home):
    for f in sorted((home / ".config/pipewire/pipewire.conf.d").glob("*.conf")):
        txt = f.read_text()
        if "combine-stream" in txt:
            m = re.search(r'node\.name\s*=\s*"([^"]+)"', txt)
            if m:
                return m.group(1)
    raise SystemExit("couldn't find the prototype's combined output")


def mic(home):
    f = home / ".local/share/speaker-sync/speaker_sync.py"
    m = re.search(r'PREFERRED_MIC\s*=\s*"([^"]*)"', f.read_text()) if f.exists() else None
    return m.group(1) if m else ""


def preset_overrides(proto_file):
    """Fields of the prototype's presets that differ from the built-in ones (taglines aside:
    the built-in ones were reworded)."""
    builtin = load_presets(None)
    raw = tomllib.loads(proto_file.read_text()) if proto_file.exists() else {}
    out = {}
    for pid, p in raw.items():
        diff = {}
        b = builtin.get(pid)
        for k, v in p.items():
            if k == "tagline" and b is not None:
                continue
            if k == "ee":
                v = EE.get(v, v)
            mine = None if b is None else (b.params.get(k) if k in b.params else getattr(b, k, None))
            if b is None or mine != v:
                diff[k] = v
        if diff:
            out[pid] = diff
    return out


def toml_presets(over):
    lines = ["# Your presets: new ones, or changes to Sounar's built-in ones (same ids).",
             "# Imported from the prototype; `sounar list` shows them all."]
    for pid, p in over.items():
        lines += ["", f"[{pid}]"] + [f"{k} = {json.dumps(v, ensure_ascii=False)}" for k, v in p.items()]
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--home", default=str(Path.home()))
    ap.add_argument("--config")
    ap.add_argument("--state")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    home = Path(a.home)
    proto_state = home / ".local/state/sounar/state.json"
    proto_presets = home / ".config/sounar/presets.toml"
    config = Path(a.config) if a.config else home / ".config/sounar"
    state_dir = Path(a.state) if a.state else home / ".local/state/sounar"

    old = json.loads(proto_state.read_text())
    if "offsets_ms" in old.get("calibration", {}):
        print(f"{proto_state} is already in Sounar 0.1's format: already imported")
        return 1
    (box, box_eq), (twin, twin_eq) = corrections(home)
    setup = Setup([Output(box, [Speaker("front-left", ["FL", "FR"], 11.0, bass_boost=False)], box_eq),
                   Output(twin, [Speaker("front-right", ["FL"], 2.0), Speaker("rear-right", ["FR"], 4.0)], twin_eq)],
                  mic=mic(home), combine_node=combine_node(home), combine_managed=False)

    cal = old.get("calibration", {})
    levels = list(cal.get("levels", {}).values())
    sync = list(old.get("sync_ms", {}).values())
    tweaks = {pid: {k: (EE.get(v, v) if k == "ee" else v) for k, v in tw.items()}
              for pid, tw in old.get("tweaks", {}).items()}
    new = {"preset": old.get("preset"), "previous": old.get("previous"), "tweaks": tweaks,
           "calibration": {"levels": dict(zip(IDS, levels, strict=False)),
                           "offsets_ms": {"front-left": 0.0, "front-right": 0.0,
                                          "rear-right": float(cal.get("align_ms", 0.0))},
                           "source": cal.get("source", "imported"), "ts": cal.get("ts")},
           "sync_ms": dict(zip(IDS[:2], sync, strict=False))}
    over = preset_overrides(proto_presets)
    hist = home / ".local/state/speaker-sync/history.jsonl"
    last = json.loads(hist.read_text().splitlines()[-1]) if hist.exists() and hist.read_text().strip() else None

    if a.dry_run:
        print(f"would write {config / 'setup.toml'}:\n{dumps(setup)}")
        print(f"would write {state_dir / 'state.json'}:\n{json.dumps(new, indent=2)}")
        print(f"would write {config / 'presets.toml'}:\n{toml_presets(over)}")
        print(f"would add the last recorded volumes to {state_dir / 'history.jsonl'}" if last else "no history")
        return 0

    if config == home / ".config/sounar" or state_dir == home / ".local/state/sounar":
        backup = home / ".local/state/sounar/prototype-backup"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(proto_state, backup / "state.json")
        if proto_presets.exists():
            shutil.copy2(proto_presets, backup / "presets.toml")
    config.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    (config / "setup.toml").write_text(dumps(setup))
    (state_dir / "state.json").write_text(json.dumps(new, indent=2) + "\n")
    (state_dir / "current").write_text((new["preset"] or "") + "\n")
    if over or proto_presets.exists():
        (config / "presets.toml").write_text(toml_presets(over))
    if last:
        entry = {"ts": datetime.now().isoformat(timespec="seconds"), "action": "import",
                 "detail": f"imported from the prototype (its last change: {last.get('ts')})",
                 "before": last["after"], "after": last["after"]}
        with open(state_dir / "history.jsonl", "a") as f:
            f.write(json.dumps(entry) + "\n")
    print(f"Imported: {config / 'setup.toml'}, {state_dir / 'state.json'}"
          + (f", {len(over)} preset change(s) in {config / 'presets.toml'}" if over else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
