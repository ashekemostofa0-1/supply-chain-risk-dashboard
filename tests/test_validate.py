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
