"""Tests for the risk project."""
import pandas as pd

from src.build_dataset import build
from src.config import INDUSTRIES, YEARS


def test_scope_has_six_industries():
    assert len(INDUSTRIES) == 6
    assert all(len(code) == 4 and code.isdigit() for code in INDUSTRIES)


def test_years_cover_2019_to_2024():
    assert YEARS == [2019, 2020, 2021, 2022, 2023, 2024]


def test_clean_table_has_one_row_per_industry_year():
    df, _ = build()
    assert len(df) == len(INDUSTRIES) * len(YEARS)
    assert not df.duplicated(["naics", "year"]).any()


def test_ratios_are_between_0_and_1():
    df, _ = build()
    for col in ["import_dep", "energy_int", "labor_int"]:
        values = df[col].dropna()
        assert ((values >= 0) & (values <= 1)).all(), col


def test_blank_cells_always_have_a_flag():
    df, _ = build()
    blank = df[["import_dep", "energy_int", "labor_int", "price_vol"]].isna().any(axis=1)
    assert (df.loc[blank, "flags"].fillna("") != "").all()
