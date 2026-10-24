"""A small simulator for PipeWire filter-graph strings (the subset Sounar writes: copy, mixer,
param_eq biquads, delay). It computes the exact frequency response from each graph input to
each graph output, so two graphs can be compared regardless of how their nodes are named."""
import math
import re

import numpy as np

RATE = 48000
N = 16384


# ---------------------------------------------------------------- parsing (SPA JSON subset)

TOKEN = re.compile(r'\s*(?:(?P<p>[{}\[\]=:,])|"(?P<s>(?:[^"\\]|\\.)*)"|(?P<w>[^\s{}\[\]=:,"]+))')


def _tokens(text):
    pos, out = 0, []
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m or m.end() == pos:
            if text[pos:].strip() == "":
                break
            raise ValueError(f"cannot parse graph near: {text[pos:pos + 40]!r}")
        pos = m.end()
        if m.group("p") is not None:
            if m.group("p") not in ",":
                out.append(("p", m.group("p")))
        elif m.group("s") is not None:
            out.append(("s", m.group("s").replace('\\"', '"')))
        else:
            out.append(("w", m.group("w")))
    return out


def _value(toks, i):
    kind, v = toks[i]
    if (kind, v) == ("p", "{"):
        obj, i = {}, i + 1
        while toks[i] != ("p", "}"):
            key = toks[i][1]
            i += 1
            if toks[i] in (("p", "="), ("p", ":")):
                i += 1
            obj[key], i = _value(toks, i)
        return obj, i + 1
    if (kind, v) == ("p", "["):
        arr, i = [], i + 1
        while toks[i] != ("p", "]"):
            item, i = _value(toks, i)
            arr.append(item)
        return arr, i + 1
    if kind == "w":
        try:
            return float(v), i + 1
        except ValueError:
            return v, i + 1
    return v, i + 1


def parse(text):
    obj, _ = _value(_tokens(text), 0)
    return obj


# ---------------------------------------------------------------- frequency responses

def freqs(n=N, rate=RATE):
    return np.fft.rfftfreq(n, 1 / rate)


def biquad(kind, freq, gain, q, rate=RATE):
    """RBJ cookbook biquad coefficients (b, a), a[0] = 1."""
    A = 10 ** (gain / 40)
    w0 = 2 * math.pi * freq / rate
    c, s = math.cos(w0), math.sin(w0)
    al = s / (2 * q)
    if kind == "lowpass":
        b, a = [(1 - c) / 2, 1 - c, (1 - c) / 2], [1 + al, -2 * c, 1 - al]
    elif kind == "highpass":
        b, a = [(1 + c) / 2, -(1 + c), (1 + c) / 2], [1 + al, -2 * c, 1 - al]
    elif kind == "peaking":
        b, a = [1 + al * A, -2 * c, 1 - al * A], [1 + al / A, -2 * c, 1 - al / A]
    elif kind == "lowshelf":
        r = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) - (A - 1) * c + r), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - r)]
        a = [(A + 1) + (A - 1) * c + r, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - r]
    elif kind == "highshelf":
        r = 2 * math.sqrt(A) * al
        b = [A * ((A + 1) + (A - 1) * c + r), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - r)]
        a = [(A + 1) - (A - 1) * c + r, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - r]
    else:
        raise ValueError(f"unknown biquad {kind}")
    return np.array(b) / a[0], np.array(a) / a[0]


def _bq_response(f, n=N, rate=RATE):
    b, a = biquad(f["type"].removeprefix("bq_"), float(f["freq"]), float(f.get("gain", 0.0)),
                  float(f.get("q", 0.707)), rate)
    z1 = np.exp(-2j * np.pi * freqs(n, rate) / rate)
    return (b[0] + b[1] * z1 + b[2] * z1 ** 2) / (a[0] + a[1] * z1 + a[2] * z1 ** 2)


def responses(text, n=N, rate=RATE):
    """Complex response, shape (2 inputs, outputs, n//2 + 1)."""
    g = parse(text)
    nodes = {nd["name"]: nd for nd in g["nodes"]}
    into = {}
    for ln in g.get("links", []):
        into.setdefault(ln["input"], []).append(ln["output"])
    inputs = g["inputs"]
    nf = n // 2 + 1
    w = 2 * np.pi * freqs(n, rate)

    def control(nd, key, default):
        return float(nd.get("control", {}).get(key, default))

    def port_in(port, src, memo):
        if port in inputs:
            return np.ones(nf, complex) if inputs.index(port) == src else np.zeros(nf, complex)
        total = np.zeros(nf, complex)
        for o in into.get(port, []):
            total = total + port_out(o, src, memo)
        return total

    def port_out(port, src, memo):
        if port in memo:
            return memo[port]
        name, pname = port.split(":", 1)
        nd = nodes[name]
        label = nd["label"]
        if label == "copy":
            y = port_in(f"{name}:In", src, memo)
        elif label == "mixer":
            y = sum(control(nd, f"Gain {i}", 1.0) * port_in(f"{name}:In {i}", src, memo) for i in range(1, 9))
        elif label == "delay":
            d = round(control(nd, "Delay (s)", 0.0) * rate)
            y = port_in(f"{name}:In", src, memo) * np.exp(-1j * w * d / rate)
        elif label == "param_eq":
            ch = pname.split()[-1]
            y = port_in(f"{name}:In {ch}", src, memo)
            for f in nd.get("config", {}).get("filters", []):
                y = y * _bq_response(f, n, rate)
        else:
            raise ValueError(f"simulator doesn't know node label {label}")
        memo[port] = y
        return y

    out = np.zeros((len(inputs), len(g["outputs"]), nf), complex)
    for src in range(len(inputs)):
        memo = {}
        for k, o in enumerate(g["outputs"]):
            out[src, k] = port_out(o, src, memo)
    return out


def impulse_responses(text, n=N, rate=RATE):
    return np.fft.irfft(responses(text, n, rate), n, axis=-1)


def equivalent(a, b, tol=1e-6):
    ra, rb = responses(a), responses(b)
    return ra.shape == rb.shape and float(np.max(np.abs(ra - rb))) < tol


def max_difference(a, b):
    ra, rb = responses(a), responses(b)
    if ra.shape != rb.shape:
        return float("inf")
    return float(np.max(np.abs(ra - rb)))
