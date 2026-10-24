import numpy as np

import sim
from sounar.graph import Graph, bq


def two_in(G, *outs):
    return G.text(["cl:In", "cr:In"], list(outs))


def test_mixer_gains():
    G = Graph()
    L, R = G.head()
    G.mixer("m", 0.5, 0.5)
    G.link(L, "m:In 1"); G.link(R, "m:In 2")
    ir = sim.impulse_responses(two_in(G, "m:Out"))
    assert ir.shape[:2] == (2, 1)
    assert abs(ir[0, 0, 0] - 0.5) < 1e-9 and abs(ir[1, 0, 0] - 0.5) < 1e-9
    assert np.max(np.abs(ir[:, :, 1:])) < 1e-9


def test_delay_shifts():
    G = Graph()
    L, _ = G.head()
    G.delay("d", 0.01)
    G.link(L, "d:In")
    ir = sim.impulse_responses(two_in(G, "d:Out"))
    assert int(np.argmax(np.abs(ir[0, 0]))) == 480
    assert np.max(np.abs(ir[1])) < 1e-12


def test_lr4_sums_flat():
    G = Graph()
    L, _ = G.head()
    G.eq("lo", bq("lowpass", 150), bq("lowpass", 150))
    G.eq("hi", bq("highpass", 150), bq("highpass", 150))
    G.link(L, "lo:In 1"); G.link(L, "hi:In 1")
    G.mixer("sum", 1.0, 1.0)
    G.link("lo:Out 1", "sum:In 1"); G.link("hi:Out 1", "sum:In 2")
    H = sim.responses(two_in(G, "sum:Out"))
    f = sim.freqs()
    band = (f >= 20) & (f <= 20000)
    mag_db = 20 * np.log10(np.abs(H[0, 0, band]))
    assert np.max(np.abs(mag_db)) < 0.01


def test_names_dont_matter():
    def chain(a, b):
        G = Graph()
        L, R = G.head()
        G.mixer(a, 0.7, 0.3)
        G.link(L, f"{a}:In 1"); G.link(R, f"{a}:In 2")
        G.eq(b, bq("peaking", 2500, 2.0, 0.8))
        G.link(f"{a}:Out", f"{b}:In 1")
        return two_in(G, f"{b}:Out 1")
    assert sim.equivalent(chain("mix", "eq"), chain("zz", "qq"))
    assert not sim.equivalent(chain("mix", "eq"), chain("mix", "eq").replace("gain = 2", "gain = 3"))


def test_signature_changes_with_graph():
    def sig(g):
        G = Graph()
        L, _ = G.head()
        G.mixer("m", g)
        G.link(L, "m:In 1")
        two_in(G, "m:Out")
        return G.ctl["snr:Gain 8"]
    assert sig(0.5) != sig(0.6)
    assert 0 <= sig(0.5) < 1


def test_controls_recorded():
    G = Graph()
    L, _ = G.head()
    G.mixer("m", 0.25)
    G.delay("d", 0.002)
    G.link(L, "m:In 1"); G.link("m:Out", "d:In")
    two_in(G, "d:Out")
    assert G.ctl["m:Gain 1"] == 0.25
    assert abs(G.ctl["d:Delay (s)"] - 0.002) < 1e-9
    assert G.ctl["snr:Gain 1"] == 1.0
