"""Tests for the dashboard calculations (Step 13)."""
from src.config import INDUSTRIES
from src.dashboard import comparison, contributions, load, scored, what_if


def test_contributions_add_up_to_the_score():
    df = load()
    for method in ("equal", "entropy", "ahp"):
        table, _ = scored(df, method)
        s = table[(table["naics"] == "3251") & (table["year"] == 2020)]["score"].iloc[0]
        c = contributions(df, "3251", 2020, method)
        assert abs(c["contribution"].sum() - s) < 1e-9, method


def test_comparison_has_every_industry_under_every_method():
    comp = comparison(load(), 2022)
    assert len(comp) == 3 * len(INDUSTRIES)


def test_what_if_zero_changes_nothing():
    res = what_if(load(), "ahp", 2024, 0, "3261")
    assert (res["score_before"] - res["score_after"]).abs().max() < 1e-12


def test_what_if_raising_imports_never_lowers_the_shocked_industry_under_fixed_weights():
    df = load()
    for method in ("equal", "ahp"):
        res = what_if(df, method, 2024, 50, "3261").set_index("naics")
        assert res.loc["3261", "score_after"] >= res.loc["3261", "score_before"] - 1e-12
