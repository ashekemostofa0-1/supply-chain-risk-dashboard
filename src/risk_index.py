"""Phase 2: the risk engine.

Step 7: normalize the four indicators to a 0-1 scale where higher means riskier.
Step 8: weight them three ways and score every industry-year:
    risk_score = sum(weight x normalized indicator)

    1. Equal weights    every indicator 0.25 (baseline)
    2. Entropy weights  from the data: indicators that vary more carry more weight
    3. AHP weights      from judgment: a 4x4 pairwise comparison matrix (AHP_MATRIX below),
                        accepted only if the consistency ratio is below 0.10

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
OUT_SCORES = os.path.join(CLEAN_DIR, "risk_scores.csv")
OUT_WEIGHTS = os.path.join(CLEAN_DIR, "weights.csv")

# ---------------------------------------------------------------------------
# AHP pairwise comparison matrix (YOUR JUDGMENT - edit and re-run to test it).
# Row i vs column j on Saaty's 1-9 scale: 1 = equally important, 3 = moderately more,
# 5 = strongly more, 7 = very strongly more, 9 = extremely more; 2, 4, 6, 8 in between.
# Below the diagonal is always the reciprocal (1/x) of the mirror cell.
#
# Order:          import_dep  energy_int  labor_int  price_vol
AHP_MATRIX = [
    [1,          2,          3,         2],    # import_dep
    [1 / 2,      1,          2,         1],    # energy_int
    [1 / 3,      1 / 2,      1,         1 / 2],  # labor_int
    [1 / 2,      1,          2,         1],    # price_vol
]
# Reasoning (put this in the report):
#   - Import dependence matters most: the 2020-2022 shocks for chemicals and plastics
#     were mainly about foreign supply (port delays, Asian feedstock, Russian fertilizer).
#   - Energy and price volatility are equal: for petroleum and chemicals, energy IS the
#     main input, so energy cost exposure and price swings move together.
#   - Labor intensity matters least: these are capital-intensive process industries
#     where payroll is a small share of output value.

# Saaty's random consistency index (RI) by matrix size n
RANDOM_INDEX = {1: 0.0, 2: 0.0, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}


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


# ----------------------------- Step 8: weights -----------------------------

def equal_weights(cols):
    """Method 1: every indicator gets the same weight (0.25 for four indicators)."""
    return pd.Series(1 / len(cols), index=cols)


def entropy_weights(norm_df, cols):
    """Method 2: Shannon entropy weights from the normalized data.

    p_ij = x_ij / sum_i x_ij                      share of row i in indicator j
    e_j  = -1/ln(n) * sum_i p_ij * ln(p_ij)       entropy (0 * ln 0 is taken as 0)
    d_j  = 1 - e_j                                degree of diversification
    w_j  = d_j / sum_j d_j                        weight
    An indicator whose values are spread evenly (high entropy) says little about which
    industry is riskier, so it gets a low weight; an uneven one gets a high weight.
    """
    X = norm_df[cols].dropna().to_numpy(dtype=float)
    n = X.shape[0]
    P = X / X.sum(axis=0)
    with np.errstate(divide="ignore", invalid="ignore"):
        plogp = np.where(P > 0, P * np.log(P), 0.0)
    e = -plogp.sum(axis=0) / np.log(n)
    d = 1 - e
    return pd.Series(d / d.sum(), index=cols)


def ahp_weights(matrix, cols):
    """Method 3: AHP weights (principal eigenvector) and consistency check.

    Returns (weights, info) where info has lambda_max, CI = (lambda_max - n)/(n - 1),
    CR = CI / RI and whether CR < 0.10.
    """
    A = np.array(matrix, dtype=float)
    n = A.shape[0]
    if A.shape != (n, n) or n != len(cols):
        raise ValueError(f"AHP matrix must be {len(cols)}x{len(cols)}")
    if not np.allclose(A * A.T, 1.0):
        raise ValueError("AHP matrix must be reciprocal: A[j][i] must equal 1 / A[i][j]")
    eigvals, eigvecs = np.linalg.eig(A)
    k = int(np.argmax(eigvals.real))
    lam = eigvals.real[k]
    w = np.abs(eigvecs[:, k].real)
    w = w / w.sum()
    ci = (lam - n) / (n - 1)
    cr = ci / RANDOM_INDEX[n] if RANDOM_INDEX[n] else 0.0
    return pd.Series(w, index=cols), {"lambda_max": lam, "CI": ci, "CR": cr, "consistent": cr < 0.10}


def score(norm_df, weights):
    """risk_score = sum(weight x normalized indicator); blank if any indicator is blank."""
    return norm_df[list(weights.index)].mul(weights, axis=1).sum(axis=1, min_count=len(weights))


def all_weights(norm_df, cols=INDICATORS, matrix=AHP_MATRIX):
    ahp, info = ahp_weights(matrix, cols)
    if not info["consistent"]:
        raise ValueError(f"AHP consistency ratio {info['CR']:.3f} is not below 0.10: "
                         "the pairwise comparisons contradict each other. Edit AHP_MATRIX.")
    weights = pd.DataFrame({"equal": equal_weights(cols), "entropy": entropy_weights(norm_df, cols),
                            "ahp": ahp})
    return weights, info


def build_scores(df):
    """Normalize, weight three ways, score, and rank within each year (1 = riskiest)."""
    norm = normalize(df, INDICATORS)
    weights, info = all_weights(norm)
    out = norm[["naics", "industry", "year"]].copy()
    for m in weights.columns:
        out[f"score_{m}"] = score(norm, weights[m])
        out[f"rank_{m}"] = out.groupby("year")[f"score_{m}"].rank(ascending=False, method="min")
    return norm, weights, info, out


def load_indicators(path=IN_FILE):
    return pd.read_csv(path, dtype={"naics": str})


def main():
    df = load_indicators()
    norm, weights, info, scores = build_scores(df)
    norm.round(4).to_csv(OUT_NORM, index=False)
    weights.round(4).rename_axis("indicator").to_csv(OUT_WEIGHTS)
    scores.round(4).to_csv(OUT_SCORES, index=False)

    print("Weights by method:")
    print(weights.round(3).to_string())
    print(f"\nAHP check: lambda_max = {info['lambda_max']:.4f}, CI = {info['CI']:.4f}, "
          f"CR = {info['CR']:.4f} -> {'consistent (below 0.10)' if info['consistent'] else 'NOT consistent'}")
    for year in (2020, 2024):
        yr = scores[scores["year"] == year].sort_values("score_equal", ascending=False)
        print(f"\nRisk scores {year} (rank 1 = riskiest):")
        cols = ["naics", "industry"] + [c for m in weights.columns for c in (f"score_{m}", f"rank_{m}")]
        print(yr[cols].round(3).to_string(index=False))
    print(f"\nSaved {OUT_NORM}, {OUT_WEIGHTS}, {OUT_SCORES}")


if __name__ == "__main__":
    main()
