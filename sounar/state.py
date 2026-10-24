"""What Sounar remembers between runs (~/.local/state/sounar): the active and previous preset,
fine-tuning per preset, the calibration and the sync delays; a history of every volume and
latency-offset change; the log; and the lock that keeps changes one at a time."""
import copy
import fcntl
import json
import os
from dataclasses import dataclass
from datetime import datetime

from sounar import SounarError, paths

EMPTY_CALIBRATION = {"levels": {}, "offsets_ms": {}, "source": "not measured", "ts": None}


def now():
    return datetime.now().isoformat(timespec="seconds")


def _state_file():
    return paths.state_dir() / "state.json"


def load_state(presets) -> dict:
    try:
        with open(_state_file()) as f:
            st = json.load(f)
    except (OSError, ValueError):
        st = {}
    st.setdefault("preset", next(iter(presets)))
    st.setdefault("previous", None)
    st.setdefault("tweaks", {})
    st.setdefault("calibration", copy.deepcopy(EMPTY_CALIBRATION))
    for k, v in EMPTY_CALIBRATION.items():
        st["calibration"].setdefault(k, copy.deepcopy(v))
    st.setdefault("sync_ms", {})
    return st


def save_state(st) -> None:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    tmp = d / "state.json.tmp"
    tmp.write_text(json.dumps(st, indent=2) + "\n")
    os.replace(tmp, _state_file())
    (d / "current").write_text(st["preset"] + "\n")     # plain preset id, for menus' check marks


@dataclass
class Effective:
    """A preset with its saved fine-tuning applied; `base` / `base_ee` are the preset's own."""
    id: str
    label: str
    tagline: str
    icon: str
    layout: str
    ee: str | None
    params: dict
    base: dict
    base_ee: str | None

    @property
    def tweaked(self):
        return self.params != self.base or self.ee != self.base_ee


def effective(st, presets, pid=None) -> Effective:
    pid = pid or st["preset"]
    if pid not in presets:
        pid = next(iter(presets))
    p = presets[pid]
    params, ee = dict(p.params), p.ee
    for k, v in st["tweaks"].get(pid, {}).items():
        if k == "ee":
            ee = v
        elif k in params:
            params[k] = v
    return Effective(p.id, p.label, p.tagline, p.icon, p.layout, ee, params, dict(p.params), p.ee)


def set_tweak(st, pid, key, value, base_value) -> None:
    """Save fine-tuning; a value equal to the preset's own is not a tweak any more."""
    tw = st["tweaks"].setdefault(pid, {})
    same = value == base_value if key == "ee" else abs(float(value) - float(base_value)) < 1e-6
    if same:
        tw.pop(key, None)
    else:
        tw[key] = value
    if not tw:
        st["tweaks"].pop(pid, None)


# ---------------------------------------------------------------- history and log

def history_append(action, before, after, detail="") -> None:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    entry = {"ts": now(), "action": action, "detail": detail, "before": before, "after": after}
    with open(d / "history.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")


def history() -> list:
    try:
        with open(paths.state_dir() / "history.jsonl") as f:
            return [json.loads(line) for line in f if line.strip()]
    except FileNotFoundError:
        return []


def log(msg) -> None:
    d = paths.state_dir()
    d.mkdir(parents=True, exist_ok=True)
    with open(d / "log", "a") as f:
        f.write(f"{now()}  {msg}\n")


# ---------------------------------------------------------------- one change at a time

def _marker():
    return paths.state_dir() / "measuring"


def measuring() -> str | None:
    """'sync' / 'calibrate' while a measurement owns the speakers, else None."""
    try:
        m = json.loads(_marker().read_text())
        os.kill(int(m["pid"]), 0)
        return m["kind"]
    except (OSError, ValueError, KeyError, TypeError):
        return None


class Measuring:
    """Marks a measurement as running, so other changes wait for it to finish."""
    def __init__(self, kind):
        self.kind = kind

    def __enter__(self):
        paths.state_dir().mkdir(parents=True, exist_ok=True)
        _marker().write_text(json.dumps({"kind": self.kind, "pid": os.getpid()}))
        return self

    def __exit__(self, *exc):
        try:
            _marker().unlink()
        except FileNotFoundError:
            pass


class Lock:
    """One change at a time (the panel, keys and the guard can overlap); refused while measuring."""
    def __init__(self, allow_measuring=False):
        self.allow = allow_measuring

    def __enter__(self):
        paths.state_dir().mkdir(parents=True, exist_ok=True)
        self.f = open(paths.state_dir() / "lock", "w")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        if not self.allow and measuring():
            self.__exit__()
            raise SounarError("the speakers are being measured; try again when it's done")
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.f, fcntl.LOCK_UN)
        self.f.close()
