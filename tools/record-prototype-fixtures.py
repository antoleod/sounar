#!/usr/bin/env python3
"""Record what the original Sounar prototype produces, so tests can prove the new engine sounds
the same for the original room (tests/test_prototype_equivalence.py).

Run on the machine the prototype is installed on; it only reads:

    python3 -I tools/record-prototype-fixtures.py ~/.local/share/speaker-sync tests/fixtures/prototype

For every preset it writes the filter graphs of both outputs (named by role, never by device),
the leveling target and the modelled loudness, for the live calibration and for a made-up
variant (other levels, the rear unit nearer, the other output synced later).
"""
import importlib.util
import json
import re
import sys
from pathlib import Path

# The prototype names its two outputs and three units after the devices; they are mapped by
# position (its own order) to role names, so no device name ends up in the repo.
ROLES = ["stereo-box", "twin"]
UNITS = ["stereo-box", "twin-front", "twin-rear"]
EE = {"Default": "Sounar Default", "Default Room": "Sounar Room", "Classical Clarity": "Sounar Classical",
      "Classical Room": "Sounar Classical Room", "Late Night": "Sounar Late Night", "Movie Night": "Sounar Movie Night"}
EQ = re.compile(r"\{ type = bq_(\w+) freq = ([-\d.]+) gain = ([-\d.]+) q = ([-\d.]+) \}")


def load(proto_dir):
    sys.path.insert(0, str(proto_dir))
    spec = importlib.util.spec_from_file_location("prototype", Path(proto_dir) / "sounar.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_eq(text):
    return [{"type": t, "freq": float(f), "gain": float(g), "q": float(q)} for t, f, g, q in EQ.findall(text)]


def main(proto_dir, out_dir):
    N = load(proto_dir)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    corr = N.correction_filters()                       # {sink: filters}, stereo box first
    sinks = list(corr)
    live = N.load_state()
    live["tweaks"] = {}
    unit_keys, sync_keys = list(N.UNITS), list(live["sync_ms"])
    role = dict(zip(sync_keys, ROLES, strict=True))
    unit = dict(zip(unit_keys, UNITS, strict=True))
    forbidden = [re.escape(k) for k in sync_keys + sinks] + [r"[0-9A-F]{2}([:_][0-9A-F]{2}){5}"]
    variant = json.loads(json.dumps(live))
    variant["calibration"] = {"levels": dict(zip(unit_keys, (0.0, -1.0, -5.5), strict=True)), "align_ms": -2.0,
                              "source": "variant", "ts": None}
    variant["sync_ms"] = dict(zip(sync_keys, (6.2, 0.0), strict=True))
    for tag, st in (("live", live), ("variant", variant)):
        for pid in N.presets():
            p = N.effective(st, pid)
            cal = st["calibration"]
            rec = {"preset": pid, "layout": p["layout"], "params": p["params"], "ee": EE.get(p["ee"], p["ee"]),
                   "state": {"levels": {unit[k]: v for k, v in cal["levels"].items()}, "align_ms": cal["align_ms"],
                             "sync_ms": {role[k]: v for k, v in st["sync_ms"].items()}},
                   "correction": {r: parse_eq(corr[s]) for r, s in zip(ROLES, sinks, strict=True)},
                   "graphs": {r: N.build(s, p, st, corr, p["layout"])[0] for r, s in zip(ROLES, sinks, strict=True)},
                   "autogain_target": N.autogain_target(p, st),
                   "loudness_db": N.loudness_db(p, st)}
            text = json.dumps(rec, indent=1, ensure_ascii=False)
            if re.search("|".join(forbidden), text, re.I):
                raise SystemExit("a device address slipped into the fixture; not writing it")
            (out / f"{tag}-{pid}.json").write_text(text + "\n")
            print(f"{tag}-{pid}: {p['layout']}, leveling {rec['autogain_target']}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    main(sys.argv[1], sys.argv[2])
