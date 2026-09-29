"""Tests for Step 10: validation."""
from src.config import INDUSTRIES
from src.validate import METHODS, validate


def test_validation_covers_all_industries_and_methods():
    table, summary = validate()
    assert len(table) == len(INDUSTRIES)
    assert sorted(summary["method"]) == sorted(METHODS)


def test_spearman_values_are_valid_correlations():
    _, summary = validate()
    for col in ["spearman_annual", "spearman_trough", "spearman_excl_petroleum"]:
        assert summary[col].between(-1, 1).all(), col


def test_ranks_are_1_to_6():
    table, _ = validate()
    for col in ["rank_actual"] + [f"rank_{m}" for m in METHODS]:
        assert sorted(table[col]) == list(range(1, len(INDUSTRIES) + 1)), col


# ---------------- Step 11: agreement ----------------
import numpy as np

from src.validate import agreement, kendalls_w


def test_kendalls_w_is_1_for_identical_rankings_and_0_for_opposite_pairs():
    same = np.array([[1, 1, 1], [2, 2, 2], [3, 3, 3], [4, 4, 4]])
    assert kendalls_w(same) == 1.0
    opposite = np.array([[1, 4], [2, 3], [3, 2], [4, 1]])
    assert kendalls_w(opposite) == 0.0


def test_agreement_tables_are_complete():
    by_year, by_ind = agreement()
    assert len(by_year) == 6 and by_year["kendall_w"].between(0, 1).all()
    assert len(by_ind) == len(INDUSTRIES)
    assert set(by_ind["verdict"]) <= {"robust high risk", "robust low risk",
                                      "method-dependent", "stable middle"}


# ---------------- Step 12: sensitivity ----------------
from src.validate import sensitivity


def test_sensitivity_full_model_is_perfectly_stable():
    sens = sensitivity().set_index("dropped")
    for m in METHODS:
        assert abs(sens.loc["none", f"{m}_stability"] - 1) < 1e-9
        assert sens.loc["none", f"{m}_top_flips"] == 0


def test_sensitivity_has_one_row_per_dropped_indicator_and_ahp_stays_consistent():
    sens = sensitivity()
    assert list(sens["dropped"]) == ["none", "import_dep", "energy_int", "labor_int", "price_vol"]
    assert (sens["ahp_cr"] < 0.10).all()
