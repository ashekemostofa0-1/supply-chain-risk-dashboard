"""Tests for Step 8: the three weighting methods."""
import numpy as np
import pandas as pd
import pytest

from src.risk_index import (AHP_MATRIX, INDICATORS, ahp_weights, build_scores, entropy_weights,
                            equal_weights, load_indicators, normalize, score)


def test_equal_weights_are_a_quarter_each():
    assert equal_weights(INDICATORS).tolist() == [0.25] * 4


def test_every_method_sums_to_one():
    _, weights, _, _ = build_scores(load_indicators())
    for m in weights.columns:
        assert weights[m].sum() == pytest.approx(1.0), m
        assert (weights[m] > 0).all(), m


def test_entropy_gives_more_weight_to_the_more_uneven_indicator():
    df = pd.DataFrame({"even": [1.0, 1.0, 1.0, 1.0], "uneven": [0.1, 0.1, 0.1, 5.0]})
    w = entropy_weights(df, ["even", "uneven"])
    assert w["uneven"] > w["even"]


def test_ahp_matrix_is_consistent():
    _, info = ahp_weights(AHP_MATRIX, INDICATORS)
    assert info["CR"] < 0.10


def test_ahp_textbook_perfectly_consistent_case():
    # weights 0.4, 0.3, 0.2, 0.1 -> A[i][j] = w_i / w_j, CR must be 0
    w = np.array([0.4, 0.3, 0.2, 0.1])
    A = w[:, None] / w[None, :]
    weights, info = ahp_weights(A, list("abcd"))
    assert np.allclose(weights.to_numpy(), w)
    assert info["CR"] == pytest.approx(0.0, abs=1e-9)


def test_ahp_rejects_contradictory_matrix():
    # a > b, b > c, but c > a strongly: circular, should fail the 0.10 check
    bad = [[1, 5, 1 / 5], [1 / 5, 1, 5], [5, 1 / 5, 1]]
    _, info = ahp_weights(bad, list("abc"))
    assert not info["consistent"]


def test_scores_are_between_0_and_1():
    _, _, _, scores = build_scores(load_indicators())
    for m in ("equal", "entropy", "ahp"):
        s = scores[f"score_{m}"].dropna()
        assert ((s >= 0) & (s <= 1)).all(), m


def test_score_is_weighted_sum():
    norm = normalize(load_indicators(), INDICATORS)
    w = equal_weights(INDICATORS)
    assert score(norm, w).iloc[0] == pytest.approx(norm.loc[0, INDICATORS].mean())
