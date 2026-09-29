"""Step 9: unit tests for the risk engine. Run with:  pytest

The four tests the assignment asks for are marked REQUIRED.
"""
import pandas as pd
import pytest

from src.build_dataset import build
from src.config import INDUSTRIES, YEARS
from src.risk_index import (AHP_MATRIX, INDICATORS, ahp_weights, build_scores,
                            equal_weights, load_indicators, normalize, score)


# ---------------- REQUIRED 1: normalized values fall between 0 and 1 ----------------

def test_normalized_values_between_0_and_1():
    norm = normalize(load_indicators(), INDICATORS)
    for c in INDICATORS:
        values = norm[c].dropna()
        assert ((values >= 0) & (values <= 1)).all(), c
        assert values.min() == 0 and values.max() == 1, c


# ---------------- REQUIRED 2: each method's weights add up to 1 ----------------

def test_each_method_weights_sum_to_1():
    _, weights, _, _ = build_scores(load_indicators())
    assert list(weights.columns) == ["equal", "entropy", "ahp"]
    for method in weights.columns:
        assert weights[method].sum() == pytest.approx(1.0), method
        assert (weights[method] > 0).all(), method


# ---------------- REQUIRED 3: made-up 3-industry example, checked by hand ----------------
#
# Raw data:            import_dep  energy_int  labor_int  price_vol
#   A                     0.10        0.02        0.05       1.0
#   B                     0.20        0.04        0.10       3.0
#   C                     0.30        0.03        0.15       1.5
#
# Min-max by hand, (x - min) / (max - min):
#   import_dep: min 0.10, max 0.30 -> A 0,  B 0.5, C 1
#   energy_int: min 0.02, max 0.04 -> A 0,  B 1,   C 0.5
#   labor_int:  min 0.05, max 0.15 -> A 0,  B 0.5, C 1
#   price_vol:  min 1.0,  max 3.0  -> A 0,  B 1,   C 0.25
#
# Equal weights (0.25 each):
#   A = 0
#   B = 0.25 * (0.5 + 1 + 0.5 + 1)    = 0.75
#   C = 0.25 * (1 + 0.5 + 1 + 0.25)   = 0.6875
#
# Custom weights (0.4, 0.3, 0.2, 0.1):
#   B = 0.4*0.5 + 0.3*1   + 0.2*0.5 + 0.1*1    = 0.70
#   C = 0.4*1   + 0.3*0.5 + 0.2*1   + 0.1*0.25 = 0.775   -> C now riskier than B

TOY = pd.DataFrame({
    "industry":   ["A", "B", "C"],
    "import_dep": [0.10, 0.20, 0.30],
    "energy_int": [0.02, 0.04, 0.03],
    "labor_int":  [0.05, 0.10, 0.15],
    "price_vol":  [1.0, 3.0, 1.5],
})


def test_toy_example_normalization_matches_hand_calculation():
    norm = normalize(TOY, INDICATORS)
    assert norm.loc[1, INDICATORS].tolist() == pytest.approx([0.5, 1, 0.5, 1])
    assert norm.loc[2, INDICATORS].tolist() == pytest.approx([1, 0.5, 1, 0.25])


def test_toy_example_equal_weight_scores_match_hand_calculation():
    s = score(normalize(TOY, INDICATORS), equal_weights(INDICATORS))
    assert s.tolist() == pytest.approx([0.0, 0.75, 0.6875])


def test_toy_example_custom_weight_scores_match_hand_calculation():
    w = pd.Series([0.4, 0.3, 0.2, 0.1], index=INDICATORS)
    s = score(normalize(TOY, INDICATORS), w)
    assert s.tolist() == pytest.approx([0.0, 0.70, 0.775])


# ---------------- REQUIRED 4: AHP consistency ratio below 0.10 ----------------

def test_ahp_consistency_ratio_below_0_10():
    _, info = ahp_weights(AHP_MATRIX, INDICATORS)
    assert info["CR"] < 0.10


# ---------------- extra checks from Steps 4 and 6 ----------------

def test_scope_has_six_industries_and_six_years():
    assert len(INDUSTRIES) == 6
    assert YEARS == [2019, 2020, 2021, 2022, 2023, 2024]


def test_clean_table_has_one_row_per_industry_year():
    df, _ = build()
    assert len(df) == len(INDUSTRIES) * len(YEARS)
    assert not df.duplicated(["naics", "year"]).any()


def test_blank_cells_always_have_a_flag():
    df, _ = build()
    blank = df[INDICATORS].isna().any(axis=1)
    assert (df.loc[blank, "flags"].fillna("") != "").all()
