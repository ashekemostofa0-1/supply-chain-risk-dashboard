"""Tests for the risk project. Scope checks now; method tests added in later steps."""
from src.config import INDUSTRIES, YEARS


def test_scope_has_six_industries():
    assert len(INDUSTRIES) == 6
    assert all(len(code) == 4 and code.isdigit() for code in INDUSTRIES)


def test_years_cover_2019_to_2024():
    assert YEARS == [2019, 2020, 2021, 2022, 2023, 2024]
