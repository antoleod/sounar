#!/usr/bin/env python3
"""Save an anonymised snapshot of what PipeWire (pactl) reports, for tests and bug reports.

    python3 -I tools/capture-pactl-fixture.py OUT_DIR [--combine NODE]

Writes sinks.json, cards.json and sink-inputs.json with only the fields Sounar reads. Bluetooth
addresses become 00_00_00_00_00_01, 02, ...; Bluetooth speaker names become "Speaker A", "B",
...; the combined output given with --combine is renamed to "sounar" / "Sounar".
"""
import json
import re
import subprocess
import sys
from pathlib import Path

MAC = re.compile(r"[0-9A-Fa-f]{2}([:_])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}")
KEEP_SINK = ("index", "name", "description", "mute", "volume", "channel_map", "active_port")
KEEP_PROPS = ("node.name", "device.name", "device.bus", "device.api", "api.bluez5.codec", "media.class",
              "application.name", "application.process.binary", "media.name")


def pactl(what):
    return json.loads(subprocess.run(["pactl", "-f", "json", "list", what], capture_output=True,
                                     text=True, check=True).stdout)


def main(out, combine=None):
    macs, names = {}, {}

    def mac(m):
        key = m.group(0).upper().replace(":", "_")
        macs.setdefault(key, f"00_00_00_00_00_{len(macs) + 1:02d}")
        return macs[key] if m.group(1) == "_" else macs[key].replace("_", ":")

    sinks = []
    for s in pactl("sinks"):
        d = {k: s[k] for k in KEEP_SINK if k in s}
        d["properties"] = {k: v for k, v in s["properties"].items() if k in KEEP_PROPS}
        if s["name"].startswith("bluez_output."):
            names.setdefault(s["description"], f"Speaker {chr(65 + len(names))}")
            d["description"] = names[s["description"]]
        sinks.append(d)
    cards = [{"name": c["name"], "properties": {k: v for k, v in c["properties"].items() if k in KEEP_PROPS},
              "ports": {p: {"latency_offset": v.get("latency_offset", "0 usec")} for p, v in c["ports"].items()}}
             for c in pactl("cards")]
    inputs = [{"index": i["index"], "sink": i["sink"], "mute": i["mute"], "corked": i.get("corked", False),
               "volume": i["volume"], "properties": {k: v for k, v in i["properties"].items() if k in KEEP_PROPS}}
              for i in pactl("sink-inputs")]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for fname, data in (("sinks.json", sinks), ("cards.json", cards), ("sink-inputs.json", inputs)):
        text = MAC.sub(mac, json.dumps(data, indent=1, ensure_ascii=False))
        for real, fake in names.items():
            text = text.replace(real, fake)
        if combine:
            text = text.replace(combine, "sounar")
        (out / fname).write_text(text + "\n")
    print(f"wrote {out}: {len(sinks)} sinks, {len(cards)} cards, {len(inputs)} streams")


if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0].startswith("-"):
        raise SystemExit(__doc__)
    comb = a[a.index("--combine") + 1] if "--combine" in a else None
    main(a[0], comb)
