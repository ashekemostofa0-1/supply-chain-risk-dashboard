"""Pure calculation helpers for the Streamlit dashboard (app.py).

Kept separate from app.py so they can be unit-tested without starting Streamlit.
"""

import pandas as pd

from src.risk_index import INDICATORS, all_weights, load_indicators, normalize, score

METHODS = {"Equal": "equal", "Entropy": "entropy", "AHP": "ahp"}
LABELS = {
    "import_dep": "Import dependence",
    "energy_int": "Energy intensity",
    "labor_int": "Labor intensity",
    "price_vol": "Price volatility",
}


def scored(df, method):
    """Normalize, weight with one method, score and rank every industry-year (1 = riskiest).

    Returns (table, weights). Entropy weights are recomputed from `df`, so a what-if change
    can shift them; equal and AHP weights are fixed.
    """
    norm = normalize(df, INDICATORS)
    weights = all_weights(norm)[0][method]
    out = norm.copy()
    out["score"] = score(norm, weights)
    out["rank"] = out.groupby("year")["score"].rank(ascending=False, method="min").astype(int)
    return out, weights


def contributions(df, naics, year, method):
    """How much each indicator adds to one industry's score: weight x normalized value."""
    table, weights = scored(df, method)
    row = table[(table["naics"] == naics) & (table["year"] == year)].iloc[0]
    return pd.DataFrame({
        "indicator": [LABELS[c] for c in INDICATORS],
        "normalized": [row[c] for c in INDICATORS],
        "weight": [weights[c] for c in INDICATORS],
        "contribution": [weights[c] * row[c] for c in INDICATORS],
    })


def comparison(df, year):
    """Score and rank of every industry under all three methods for one year."""
    parts = []
    for name, m in METHODS.items():
        t, _ = scored(df, m)
        t = t[t["year"] == year][["naics", "industry", "score", "rank"]].copy()
        t["method"] = name
        parts.append(t)
    return pd.concat(parts, ignore_index=True)


def what_if(df, method, year, pct, naics=None):
    """Raise import dependence by `pct` percent (relative, capped at 1.0) and rescore.

    naics=None applies the shock to every industry; otherwise only to that one.
    Returns the selected year with score/rank before and after, sorted by the new rank.
    """
    shocked = df.copy()
    mask = shocked["year"] == year
    if naics is not None:
        mask &= shocked["naics"] == naics
    shocked.loc[mask, "import_dep"] = (shocked.loc[mask, "import_dep"] * (1 + pct / 100)).clip(upper=1.0)

    before, _ = scored(df, method)
    after, _ = scored(shocked, method)
    keep = ["naics", "industry", "score", "rank"]
    b = before[before["year"] == year][keep]
    a = after[after["year"] == year][["naics", "score", "rank"]]
    out = b.merge(a, on="naics", suffixes=("_before", "_after"))
    out["rank_change"] = out["rank_before"] - out["rank_after"]  # positive = moved up (riskier)
    return out.sort_values("rank_after").reset_index(drop=True)


def load():
    return load_indicators()
