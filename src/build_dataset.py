"""Step 6: clean and merge the raw files into one table, one row per industry per year.

Run from the project folder:
    python -m src.build_dataset

Output
    data/clean/risk_indicators.csv   naics | industry | year | import_dep | energy_int |
                                     labor_int | price_vol | source | flags
    data/clean/risk_inputs.csv       the raw numbers behind every ratio (for checking)

Indicator definitions
    import_dep  = imports / (shipments + imports - exports)       share of U.S. demand met by imports
    energy_int  = (electricity cost + fuel cost) / shipments      energy cost per $ of output
    labor_int   = annual payroll / shipments                      payroll cost per $ of output
    price_vol   = standard deviation of the month-to-month % change in the industry's
                  Producer Price Index within the calendar year (percentage points).
                  The % change is used instead of the index level because every PPI series
                  has its own base year, so raw levels are not comparable across industries.

Missing data policy (chosen: LEAVE BLANK AND FLAG, never interpolate)
    If an input is missing, suppressed by Census, or zero, the indicator is left blank and
    the reason is written in the `flags` column. With only six years per industry,
    interpolating would invent values in exactly the years that matter most (the 2020-2022
    disruption), so a visible gap is more honest than a smooth guess.

Known series break (documented, not "fixed")
    2019-2021 come from the Annual Survey of Manufactures (value of shipments),
    2022 from the Economic Census (value of shipments), and 2023-2024 from the Annual
    Integrated Economic Survey, which reports total REVENUE instead of shipments.
    Rows from AIES carry the flag "revenue_not_shipments".
"""

import json
import os

import numpy as np
import pandas as pd

from src.config import CLEAN_DIR, INDUSTRIES, RAW_DIR, YEARS
from src.download_data import PPI_SERIES

OUT_MAIN = os.path.join(CLEAN_DIR, "risk_indicators.csv")
OUT_INPUTS = os.path.join(CLEAN_DIR, "risk_inputs.csv")
MIN_PPI_MONTHS = 10  # need at least 10 monthly changes to trust a yearly volatility


# ---------- readers (each returns None when the file is missing or empty) ----------

def read_census(path):
    """Census API JSON -> dict of the first data row, e.g. {'RCPTOT': '178752379', ...}."""
    full = os.path.join(RAW_DIR, path)
    if not os.path.exists(full):
        return None
    with open(full, encoding="utf-8") as f:
        rows = json.load(f)
    if len(rows) < 2:
        return None
    return dict(zip(rows[0], rows[1]))


def num(value):
    """Census strings -> float. Suppressed or non-numeric codes (e.g. 'D', 'N', 'X') -> NaN."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return np.nan
    return x if x > 0 else np.nan


def trade_total(path, value_col):
    """World total (CTY_CODE '-', 'TOTAL FOR ALL COUNTRIES') from a trade file, in dollars."""
    full = os.path.join(RAW_DIR, path)
    if not os.path.exists(full):
        return np.nan
    with open(full, encoding="utf-8") as f:
        rows = json.load(f)
    header = rows[0]
    i_cty, i_val = header.index("CTY_CODE"), header.index(value_col)
    for r in rows[1:]:
        if r[i_cty] == "-":
            return num(r[i_val])
    return np.nan


def census_inputs(naics, year):
    """Shipments, payroll and energy cost (all $1,000) plus which survey they came from."""
    if year <= 2021:
        d = read_census(f"census_asm/asm_{naics}_{year}.json") or {}
        return dict(source="ASM", shipments=num(d.get("RCPTOT")), payroll=num(d.get("PAYANN")),
                    electricity=num(d.get("CSTELEC")), fuel=num(d.get("CSTFU")))
    if year == 2022:
        d = read_census(f"census_ec/ec_{naics}_2022.json") or {}
        return dict(source="Economic Census", shipments=num(d.get("RCPTOT")),
                    payroll=num(d.get("PAYANN")), electricity=num(d.get("CSTELEC")),
                    fuel=num(d.get("CSTFU")))
    b = read_census(f"census_aies/aies_basic_{naics}_{year}.json") or {}
    e = read_census(f"census_aies/aies_exp_{naics}_{year}.json") or {}
    return dict(source="AIES", shipments=num(b.get("RCPT_TOT_VAL")), payroll=num(b.get("PAY_ANN_VAL")),
                electricity=num(e.get("EXPS_ELEC_VAL")), fuel=num(e.get("EXPS_FUEL_VAL")))


def ppi_volatility(naics):
    """Return {year: (volatility, number of monthly changes used)} for one industry."""
    path = os.path.join(RAW_DIR, "fred_ppi", f"{PPI_SERIES[naics]}.csv")
    if not os.path.exists(path):
        return {}
    df = pd.read_csv(path)
    df.columns = ["date", "ppi"]
    df["date"] = pd.to_datetime(df["date"])
    df["ppi"] = pd.to_numeric(df["ppi"], errors="coerce")  # FRED marks gaps with '.' or blank
    df = df.sort_values("date")
    # % change vs the previous month, only when the previous month exists (no bridging gaps)
    prev = df["ppi"].shift(1)
    consecutive = df["date"].shift(1) == df["date"] - pd.DateOffset(months=1)
    df["chg"] = np.where(consecutive, (df["ppi"] / prev - 1) * 100, np.nan)
    out = {}
    for year in YEARS:
        chg = df.loc[df["date"].dt.year == year, "chg"].dropna()
        out[year] = (chg.std(ddof=1) if len(chg) >= 2 else np.nan, len(chg))
    return out


# ---------- build ----------

def build():
    records = []
    for naics, industry in INDUSTRIES.items():
        vol = ppi_volatility(naics)
        for year in YEARS:
            c = census_inputs(naics, year)
            imports = trade_total(f"census_trade/imports_{naics}_{year}.json", "GEN_VAL_YR")
            exports = trade_total(f"census_trade/exports_{naics}_{year}.json", "ALL_VAL_YR")
            ship_usd = c["shipments"] * 1000  # Census reports $1,000; trade is in dollars
            flags = []

            if c["source"] == "AIES":
                flags.append("revenue_not_shipments")
            if np.isnan(c["shipments"]):
                flags.append("shipments_missing")

            # import dependence
            demand = ship_usd + imports - exports
            if np.isnan(imports) or np.isnan(exports):
                flags.append("trade_missing")
                import_dep = np.nan
            elif np.isnan(demand) or demand <= 0:
                if not np.isnan(demand):
                    flags.append("apparent_demand_not_positive")
                import_dep = np.nan
            else:
                import_dep = imports / demand

            # energy intensity
            if np.isnan(c["electricity"]) or np.isnan(c["fuel"]):
                flags.append("energy_cost_missing")
            energy_int = (c["electricity"] + c["fuel"]) / c["shipments"]

            # labor intensity
            if np.isnan(c["payroll"]):
                flags.append("payroll_missing")
            labor_int = c["payroll"] / c["shipments"]

            # price volatility
            v, n = vol.get(year, (np.nan, 0))
            if n < MIN_PPI_MONTHS:
                flags.append(f"ppi_only_{n}_months")
                v = np.nan

            records.append(dict(
                naics=naics, industry=industry, year=year,
                import_dep=import_dep, energy_int=energy_int, labor_int=labor_int, price_vol=v,
                source=c["source"], flags=";".join(flags),
                shipments_k=c["shipments"], payroll_k=c["payroll"],
                electricity_k=c["electricity"], fuel_k=c["fuel"],
                imports_usd=imports, exports_usd=exports, ppi_months=n,
            ))

    df = pd.DataFrame(records)
    main_cols = ["naics", "industry", "year", "import_dep", "energy_int", "labor_int",
                 "price_vol", "source", "flags"]
    input_cols = ["naics", "industry", "year", "source", "shipments_k", "payroll_k",
                  "electricity_k", "fuel_k", "imports_usd", "exports_usd", "ppi_months"]
    return df[main_cols], df[input_cols]


def main():
    main_df, inputs_df = build()
    os.makedirs(CLEAN_DIR, exist_ok=True)
    main_df.round(6).to_csv(OUT_MAIN, index=False)
    inputs_df.to_csv(OUT_INPUTS, index=False)

    indicators = ["import_dep", "energy_int", "labor_int", "price_vol"]
    blanks = int(main_df[indicators].isna().sum().sum())
    print(f"Wrote {OUT_MAIN}: {len(main_df)} rows "
          f"({main_df['naics'].nunique()} industries x {main_df['year'].nunique()} years)")
    print(f"Blank indicator cells: {blanks} of {len(main_df) * len(indicators)} (see 'flags')")
    with pd.option_context("display.width", 140, "display.max_columns", 20):
        print(main_df.drop(columns="flags").round(4).to_string(index=False))


if __name__ == "__main__":
    main()
