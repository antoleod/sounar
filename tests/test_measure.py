import numpy as np
import pytest

from sounar.measure import RATE, band_db, chirp, detect_arrivals, pink_noise


def place(track_len, items, lead=0.5, noise=0.0, seed=3):
    """A recording: each (signal, start sample, delay ms, gain dB) lands lead + delay later."""
    rec = np.zeros(track_len + int(2 * RATE))
    for sig, start, delay_ms, gain_db in items:
        at = start + int(round((lead + delay_ms / 1000) * RATE))
        rec[at:at + len(sig)] += sig * 10 ** (gain_db / 20)
    return rec + noise * np.random.default_rng(seed).standard_normal(len(rec))


def test_detects_delay_in_noise():
    c = chirp()
    starts = [int(1.0 * RATE), int(2.0 * RATE)]
    rec = place(int(3 * RATE), [(c, starts[0], 100.0, -20), (c, starts[1], 312.5, -20)], noise=0.01 * 0.1)
    a = detect_arrivals(rec, starts, c)
    assert a[1] - a[0] == pytest.approx(212.5, abs=0.1)


def test_rejects_silence():
    c = chirp()
    starts = [int(1.0 * RATE), int(2.0 * RATE)]
    rec = place(int(3 * RATE), [], noise=0.01)
    assert detect_arrivals(rec, starts, c) == [None, None]


def test_ignores_click_outside_window():
    c = chirp()
    starts = [int(1.0 * RATE)]
    rec = place(int(3 * RATE), [(c, starts[0], 200.0, -20)], noise=0.0005)
    rec[int(1.2 * RATE)] = 0.9                       # a click before the window opens
    a = detect_arrivals(rec, starts, c)
    assert a[0] == pytest.approx(700.0, abs=0.5)


def test_levels_known():
    n = pink_noise(2.0)
    assert band_db(n * 10 ** (-6 / 20), 200, 5000) - band_db(n, 200, 5000) == pytest.approx(-6.0, abs=0.3)


def test_pink_noise_level():
    n = pink_noise(1.0)
    assert np.sqrt(np.mean(n ** 2)) == pytest.approx(0.12, rel=0.01)
