"""`sounar doctor`: a report to paste into a bug report. Device addresses, device names,
nicknames, the home directory, user and host names are stripped out."""
import getpass
import os
import platform
import re
import shutil
import socket
import subprocess
import sys

import numpy as np

from sounar import __version__, paths
from sounar.state import effective, load_state

MAC = re.compile(r"[0-9A-Fa-f]{2}([:_])[0-9A-Fa-f]{2}(?:\1[0-9A-Fa-f]{2}){4}")


def anonymise(text, setup=None) -> str:
    if setup:
        for i, o in enumerate(setup.outputs, 1):
            if o.node:
                text = text.replace(o.node, f"output-{i}")
            for s in o.speakers:
                if s.nickname:
                    text = text.replace(s.nickname, "(nickname)")
    text = MAC.sub(lambda m: "XX_XX_XX_XX_XX_XX" if m.group(1) == "_" else "XX:XX:XX:XX:XX:XX", text)
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "~")
    for word, sub in ((getpass.getuser(), "user"), (socket.gethostname(), "host")):
        if word and len(word) > 2:
            text = re.sub(rf"\b{re.escape(word)}\b", sub, text)
    return text


def _cmd(*args):
    if not shutil.which(args[0]):
        return "not installed"
    r = subprocess.run(args, capture_output=True, text=True, check=False)
    return (r.stdout or r.stderr).strip().splitlines()[-1:] or ["?"]


def report(ctx) -> str:
    lines = ["## Sounar doctor", "",
             f"- Sounar {__version__}, Python {platform.python_version()}, NumPy {np.__version__}, "
             f"{sys.platform}",
             f"- PipeWire {'.'.join(map(str, ctx.pw.version()))}, WirePlumber {_cmd('wireplumber', '--version')[0]}",
             f"- Easy Effects: {'available' if ctx.ee.available() else 'not available'}"
             f" ({_cmd('easyeffects', '--version')[0] if ctx.ee.available() else '-'})",
             f"- Desktop: {os.environ.get('XDG_CURRENT_DESKTOP', '?')}, "
             f"Omarchy: {'yes' if shutil.which('omarchy') else 'no'}"]
    if ctx.setup is None:
        lines.append("- Setup: none yet")
    else:
        sinks = {s.name: s for s in ctx.pw.sinks()}
        lines.append(f"- Setup: {len(ctx.setup.outputs)} output(s), combined output "
                     f"{'managed by Sounar' if ctx.setup.combine_managed else 'existing'}")
        for i, o in enumerate(ctx.setup.outputs, 1):
            s = sinks.get(o.node)
            kind = f"{s.bus}, {s.codec or '-'}, channels {'/'.join(s.channels)}" if s else "not connected"
            spk = "; ".join(f"{x.id} @ {'sub' if x.sub else f'{x.at:g}'} ({'/'.join(x.channels)}"
                            f"{', no bass boost' if not x.bass_boost else ''})" for x in o.speakers)
            lines.append(f"  - output {i} ({kind}): {spk}" + (", correction EQ" if o.correction else ""))
    st = load_state(ctx.presets)
    eff = effective(st, ctx.presets)
    cal = st["calibration"]
    lines += [f"- Preset: {eff.label} ({eff.id}, {eff.layout}), fine-tuned: {bool(st['tweaks'].get(eff.id))}",
              f"- Calibration: {cal['source']} {cal['ts'] or ''}; sync {st['sync_ms'] or 'none'}",
              f"- Services: guard {ctx.pw.unit_active('sounar-guard.service')}, "
              f"keep-alive {ctx.pw.unit_active('sounar-keepalive.service')}"]
    if ctx.setup is not None:
        from sounar.core import verify
        lines.append(f"- Graphs match the preset: {not verify(ctx, st)}")
    lines += ["", "Recent log:", "```"]
    try:
        lines += (paths.state_dir() / "log").read_text().splitlines()[-20:]
    except OSError:
        lines.append("(no log yet)")
    lines.append("```")
    return anonymise("\n".join(lines), ctx.setup)
