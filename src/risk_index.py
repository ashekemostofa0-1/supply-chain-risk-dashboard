"""Phase 2: the risk engine.

Step 7: normalize the four indicators to a 0-1 scale where higher means riskier.
(Steps 8+ add the three weighting methods to this file.)

Run from the project folder:
    python -m src.risk_index

Normalization choice (for the report)
    Min-max scaling is applied over the POOLED panel: all 6 industries x 6 years at once.
    So 0 = the lowest value seen in any industry in any year, 1 = the highest.
    This keeps scores comparable across years (a rise from 2019 to 2022 is a real rise),
    which scaling each year separately would hide.

    All four indicators already point the same way (higher = more exposed), so none
    needs to be flipped:
      import_dep  more reliance on foreign supply
      energy_int  more exposure to energy price shocks
      labor_int   more exposure to wage and labor-shortage shocks
      price_vol   less predictable input/output prices
"""

import os

import numpy as np
import pandas as pd

from src.config import CLEAN_DIR

INDICATORS = ["import_dep", "energy_int", "labor_int", "price_vol"]
IN_FILE = os.path.join(CLEAN_DIR, "risk_indicators.csv")
OUT_NORM = os.path.join(CLEAN_DIR, "risk_normalized.csv")


def normalize(df, cols):
    """Min-max scale each column to 0-1 (higher = riskier).

    Same formula as the assignment, with two safety rules:
      - blank cells stay blank (NaN is ignored by min/max and passes through)
      - a column with a single repeated value becomes 0 instead of dividing by zero
    """
    out = df.copy()
    for c in cols:
        lo, hi = df[c].min(), df[c].max()
        if pd.isna(lo) or hi == lo:
            out[c] = np.where(df[c].isna(), np.nan, 0.0)
        else:
            out[c] = (df[c] - lo) / (hi - lo)
    return out


def load_indicators(path=IN_FILE):
    return pd.read_csv(path, dtype={"naics": str})


def main():
    df = load_indicators()
    norm = normalize(df, INDICATORS)
    norm.round(4).to_csv(OUT_NORM, index=False)
    print(f"Wrote {OUT_NORM} ({len(norm)} rows). Scale: 0 = lowest in panel, 1 = highest.\n")
    print("Min and max of each raw indicator (these become 0 and 1):")
    for c in INDICATORS:
        lo, hi = df.loc[df[c].idxmin()], df.loc[df[c].idxmax()]
        print(f"  {c:<11} min {lo[c]:.4f} ({lo['naics']} {lo['year']})   "
              f"max {hi[c]:.4f} ({hi['naics']} {hi['year']})")
    print()
    print(norm[["naics", "industry", "year"] + INDICATORS].round(3).to_string(index=False))


if __name__ == "__main__":
    main()
