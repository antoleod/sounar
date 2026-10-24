"""Desktop pieces: notifications (any desktop), the preset menu (`sounar menu`), and the
Omarchy menu rows. Everything here only reads presets and state and runs `sounar` commands."""
import json
import re
import shutil
import subprocess
import sys

from sounar import paths

LAUNCHERS = {
    "walker": ["walker", "--dmenu"],
    "fuzzel": ["fuzzel", "--dmenu", "--prompt", "Sounar "],
    "rofi": ["rofi", "-dmenu", "-i", "-p", "Sounar"],
    "wofi": ["wofi", "--dmenu", "-p", "Sounar"],
    "bemenu": ["bemenu", "-p", "Sounar"],
    "dmenu": ["dmenu", "-i", "-p", "Sounar"],
}
OMARCHY = ["omarchy-menu", "summon", "sounar"]


def notify(title, body="", icon="audio-speakers"):
    """A desktop notification that replaces Sounar's previous one."""
    if not shutil.which("notify-send"):
        return
    subprocess.run(["notify-send", "-a", "Sounar", "-i", icon,
                    "-h", "string:x-canonical-private-synchronous:sounar", title, body], check=False)


def launcher(pref="auto", which=shutil.which):
    """The command that shows the menu: the Omarchy menu, else the first dmenu-style launcher."""
    if pref == "terminal":
        return None
    if pref in ("auto", "omarchy") and which("omarchy-menu"):
        return list(OMARCHY)
    order = list(LAUNCHERS) if pref == "auto" else [pref]
    for name in order:
        if name in LAUNCHERS and which(name):
            return list(LAUNCHERS[name])
    return None


def menu_lines(presets, current):
    lines, actions = [], []
    for pid, p in presets.items():
        lines.append(f"{'✓' if pid == current else ' '} {p.icon}  {p.label} — {p.tagline}")
        actions.append(("set", pid))
    lines += ["  󰓅  Sync speakers — after a reconnect: ~15 s of chirps, music paused",
              "  󰔡  Calibrate — once, or after moving a speaker: ~1 min of test sounds"]
    actions += [("sync",), ("calibrate",)]
    return lines, actions


def menu(presets, current, pref="auto", run=subprocess.run):
    """Show the menu and return the chosen action, or None."""
    cmd = launcher(pref)
    if cmd == OMARCHY:
        refresh_omarchy_menu(presets)
        run(cmd, check=False)
        return None
    lines, actions = menu_lines(presets, current)
    if cmd:
        r = run(cmd, input="\n".join(lines) + "\n", capture_output=True, text=True, check=False)
        choice = (r.stdout or "").rstrip("\n")
        return actions[lines.index(choice)] if choice in lines else None
    if not sys.stdin.isatty():
        notify("Sounar", "No menu launcher found (fuzzel, rofi, wofi, walker, bemenu or dmenu)")
        return None
    for i, line in enumerate(lines, 1):
        print(f"{i:2d} {line}")
    try:
        n = int(input("number: "))
    except (ValueError, EOFError):
        return None
    return actions[n - 1] if 1 <= n <= len(actions) else None


# ---------------------------------------------------------------- Omarchy

def omarchy_menu_file():
    return paths.xdg_config_home() / "omarchy/extensions/omarchy-menu.jsonc"


def omarchy_rows(presets) -> dict:
    current = paths.state_dir() / "current"
    rows = {"sounar": {"icon": "󰓃", "label": "Sounar", "aliases": ["sound", "speakers", "sounar"],
                       "description": "Speaker presets: layout, balance, delay and effects"}}
    for pid, p in presets.items():
        rows[f"sounar.{pid}"] = {"icon": p.icon, "label": p.label, "description": p.tagline,
                                 "action": f"sounar set {pid}",
                                 "checked": f'[ "$(cat {current} 2>/dev/null)" = "{pid}" ]'}
    rows["sounar.zsync"] = {"icon": "󰓅", "label": "Sync speakers",
                            "description": "After a reconnect: ~15 s of chirps, music paused", "action": "sounar sync"}
    rows["sounar.zcalibrate"] = {"icon": "󰔡", "label": "Calibrate",
                                 "description": "Once, or after moving a speaker: ~1 min of test sounds",
                                 "action": "sounar calibrate"}
    return rows


def write_omarchy_menu(path, presets) -> None:
    """Write the Sounar rows into the Omarchy menu extension file, keeping everything else."""
    try:
        txt = path.read_text()
    except OSError:
        txt = "{\n}\n"
    txt = re.sub(r"\n[ \t]*// sounar:begin.*?// sounar:end[^\n]*\n", "\n", txt, flags=re.S)
    block = "\n  // sounar:begin (written by `sounar menu-install`; edit ~/.config/sounar/presets.toml instead)\n"
    block += "".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n"
                     for k, v in omarchy_rows(presets).items())
    block += "  // sounar:end\n"
    i = txt.rindex("}")
    txt = txt[:i].rstrip() + "\n" + block + txt[i:]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(txt)
    tmp.replace(path)


def refresh_omarchy_menu(presets) -> None:
    """Bring the Omarchy menu rows up to date when the presets changed (Omarchy only)."""
    if not shutil.which("omarchy-menu"):
        return
    f = omarchy_menu_file()
    sources = [p for p in (paths.user_presets_file(), paths.package_data() / "presets.toml") if p.exists()]
    try:
        newest = max(p.stat().st_mtime for p in sources)
        stale = "sounar:begin" not in f.read_text() or newest > f.stat().st_mtime
    except (OSError, ValueError):
        stale = True
    if stale:
        write_omarchy_menu(f, presets)
