"""Tests for Step 7: min-max normalization."""
import numpy as np
import pandas as pd

from src.risk_index import INDICATORS, load_indicators, normalize


def test_normalize_simple_example():
    df = pd.DataFrame({"x": [2.0, 4.0, 6.0]})
    assert normalize(df, ["x"])["x"].tolist() == [0.0, 0.5, 1.0]


def test_normalize_keeps_blanks_and_handles_constant_column():
    df = pd.DataFrame({"x": [1.0, np.nan, 3.0], "y": [5.0, 5.0, 5.0]})
    out = normalize(df, ["x", "y"])
    assert np.isnan(out.loc[1, "x"])
    assert out["y"].tolist() == [0.0, 0.0, 0.0]


def test_real_data_is_scaled_0_to_1():
    out = normalize(load_indicators(), INDICATORS)
    for c in INDICATORS:
        assert out[c].min() == 0 and out[c].max() == 1, c


def test_normalize_does_not_change_the_input():
    df = load_indicators()
    before = df.copy()
    normalize(df, INDICATORS)
    pd.testing.assert_frame_equal(df, before)
