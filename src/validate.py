"""Step 10: validation test - which weighting method predicted real disruption best?
Step 11: agreement test - do the three methods rank the industries the same way?
Step 12: sensitivity test - drop one indicator at a time and recalculate.

Run from the project folder:
    python -m src.validate

Method
    1. Rank the six industries by their 2019 risk score under each method
       (equal, entropy, AHP). 2019 is the last year BEFORE the shock, so the score is a
       genuine prediction: it uses no information from 2020.
    2. Rank them by their actual output drop in 2020, from FRED industrial production:
           drop_annual = (average 2019 IP - average 2020 IP) / average 2019 IP
       A bigger drop means the industry was hit harder.
    3. Compare each method's ranking with reality using Spearman's rank correlation
       (scipy.stats.spearmanr). +1 = perfect match, 0 = no relation, -1 = reversed.
    4. The method with the highest correlation predicted real disruption best.

Robustness check
    The same test is repeated with a second definition of the shock, the worst single
    month of 2020 compared with the 2019 average ("drop_trough"), which captures the
    sharp April 2020 collapse that an annual average smooths out.

Sensitivity check (reported separately, never replaces the main result)
    Petroleum's 2020 drop was mainly a DEMAND collapse (lockdowns cut fuel use), which a
    supply-chain exposure index is not designed to predict. The test is repeated without
    petroleum to show how much that one industry drives the result.

Step 11 agreement test
    For every year 2019-2024 the three methods each rank the six industries (1 = riskiest).
      - Pairwise Spearman between methods (equal vs entropy, equal vs AHP, entropy vs AHP)
      - Kendall's W across all three methods: 1 = identical rankings, 0 = no agreement
          W = 12 * S / (m^2 * (n^3 - n)),  m = 3 methods, n = 6 industries,
          S = sum of squared deviations of each industry's rank-sum from the mean rank-sum
      - Per industry, over all 18 method-year rankings:
          "robust high risk"  ranked 1-2 in at least 80% of them
          "robust low risk"   ranked 5-6 in at least 80% of them
          "method-dependent"  in the same year, the methods disagree by 3+ places at least once
          "stable middle"     everything else

Step 12 sensitivity test
    For each indicator, remove it, rebuild all three methods on the remaining three
    (equal = 1/3 each, entropy recomputed, AHP = same matrix without that row/column, CR
    rechecked), and rescore 2019-2024. For each method report:
      stability  mean Spearman (over the 6 years) between the full ranking and the reduced one.
                 Near 1 = the dropped indicator changes little. Low = it was doing most of the work.
      top_flips  number of years (of 6) where the #1 riskiest industry changes.
      valid_rho  Step 10 validation rho (2019 score vs 2020 output drop) without that indicator.

Caution for the report
    With only six industries, a correlation needs to be about 0.89 or higher to be
    statistically significant at the 5% level, so p-values are printed but the result
    should be read as evidence, not proof.
"""

import os

import pandas as pd
from scipy.stats import spearmanr

from src.config import CLEAN_DIR, INDUSTRIES, RAW_DIR
from src.download_data import IP_SERIES
from src.risk_index import (AHP_MATRIX, INDICATORS, ahp_weights, build_scores, entropy_weights,
                            equal_weights, load_indicators, normalize, score)

METHODS = ["equal", "entropy", "ahp"]
BASE_YEAR, SHOCK_YEAR = 2019, 2020
OUT_FILE = os.path.join(CLEAN_DIR, "validation.csv")
OUT_SUMMARY = os.path.join(CLEAN_DIR, "validation_summary.csv")
OUT_AGREE_YEAR = os.path.join(CLEAN_DIR, "agreement_by_year.csv")
OUT_AGREE_IND = os.path.join(CLEAN_DIR, "agreement_by_industry.csv")
OUT_SENS = os.path.join(CLEAN_DIR, "sensitivity.csv")


def output_drops():
    """Per industry: 2020 output drop from FRED industrial production (positive = fell)."""
    rows = []
    for naics in INDUSTRIES:
        sid = IP_SERIES[naics]
        df = pd.read_csv(os.path.join(RAW_DIR, "fred_ip", f"{sid}.csv"))
        df.columns = ["date", "ip"]
        df["date"] = pd.to_datetime(df["date"])
        df["ip"] = pd.to_numeric(df["ip"], errors="coerce")
        base = df.loc[df["date"].dt.year == BASE_YEAR, "ip"].mean()
        shock = df.loc[df["date"].dt.year == SHOCK_YEAR, "ip"]
        rows.append(dict(naics=naics, ip_series=sid,
                         drop_annual=(base - shock.mean()) / base,
                         drop_trough=(base - shock.min()) / base))
    return pd.DataFrame(rows)


def validate():
    _, _, _, scores = build_scores(load_indicators())
    pre = scores[scores["year"] == BASE_YEAR][["naics", "industry"] + [f"score_{m}" for m in METHODS]]
    table = pre.merge(output_drops(), on="naics")

    # ranks: 1 = highest predicted risk / biggest actual drop
    for m in METHODS:
        table[f"rank_{m}"] = table[f"score_{m}"].rank(ascending=False).astype(int)
    table["rank_actual"] = table["drop_annual"].rank(ascending=False).astype(int)

    summary = []
    for m in METHODS:
        rho_a, p_a = spearmanr(table[f"score_{m}"], table["drop_annual"])
        rho_t, p_t = spearmanr(table[f"score_{m}"], table["drop_trough"])
        ex = table[table["naics"] != "3241"]
        rho_x, p_x = spearmanr(ex[f"score_{m}"], ex["drop_annual"])
        summary.append(dict(method=m, spearman_annual=rho_a, p_annual=p_a,
                            spearman_trough=rho_t, p_trough=p_t,
                            spearman_excl_petroleum=rho_x, p_excl_petroleum=p_x))
    summary = pd.DataFrame(summary).sort_values("spearman_annual", ascending=False)
    return table, summary


# ----------------------------- Step 11: agreement -----------------------------

def kendalls_w(rank_matrix):
    """Kendall's coefficient of concordance. rank_matrix: rows = items, columns = raters."""
    R = rank_matrix.sum(axis=1)
    n, m = rank_matrix.shape
    S = ((R - R.mean()) ** 2).sum()
    return 12 * S / (m ** 2 * (n ** 3 - n))


def agreement():
    """Return (per-year agreement table, per-industry robustness table)."""
    _, _, _, scores = build_scores(load_indicators())
    rank_cols = [f"rank_{m}" for m in METHODS]
    pairs = [("equal", "entropy"), ("equal", "ahp"), ("entropy", "ahp")]

    by_year = []
    for year, g in scores.groupby("year"):
        row = {"year": year, "kendall_w": kendalls_w(g[rank_cols].to_numpy())}
        for a, b in pairs:
            row[f"rho_{a}_{b}"] = spearmanr(g[f"score_{a}"], g[f"score_{b}"])[0]
        by_year.append(row)
    by_year = pd.DataFrame(by_year)

    by_ind = []
    for naics, g in scores.groupby("naics"):
        ranks = g[rank_cols].to_numpy().ravel()
        spread = (g[rank_cols].max(axis=1) - g[rank_cols].min(axis=1)).max()
        share_top = (ranks <= 2).mean()
        share_bottom = (ranks >= 5).mean()
        if share_top >= 0.8:
            verdict = "robust high risk"
        elif share_bottom >= 0.8:
            verdict = "robust low risk"
        elif spread >= 3:
            verdict = "method-dependent"
        else:
            verdict = "stable middle"
        by_ind.append(dict(naics=naics, industry=g["industry"].iloc[0],
                           mean_rank=ranks.mean(), best_rank=int(ranks.min()),
                           worst_rank=int(ranks.max()), max_same_year_spread=int(spread),
                           share_top2=share_top, verdict=verdict))
    by_ind = pd.DataFrame(by_ind).sort_values("mean_rank")
    return by_year, by_ind


# ----------------------------- Step 12: sensitivity -----------------------------

def weights_for(norm, cols):
    """Equal, entropy and AHP weights using only `cols` (AHP sub-matrix keeps your judgments)."""
    idx = [INDICATORS.index(c) for c in cols]
    sub = [[AHP_MATRIX[i][j] for j in idx] for i in idx]
    ahp, info = ahp_weights(sub, cols)
    w = {"equal": equal_weights(cols), "entropy": entropy_weights(norm, cols), "ahp": ahp}
    return w, info["CR"]


def ranks_by_year(norm, w):
    s = norm[["naics", "year"]].copy()
    s["score"] = score(norm, w)
    s["rank"] = s.groupby("year")["score"].rank(ascending=False, method="min")
    return s


def sensitivity():
    """One row per dropped indicator ('none' = full model), columns per method."""
    df = load_indicators()
    norm = normalize(df, INDICATORS)
    drops = output_drops().set_index("naics")["drop_annual"]
    full_w, _ = weights_for(norm, INDICATORS)
    full = {m: ranks_by_year(norm, full_w[m]) for m in METHODS}

    rows = []
    for dropped in ["none"] + INDICATORS:
        cols = [c for c in INDICATORS if c != dropped]
        w, cr = weights_for(norm, cols)
        row = {"dropped": dropped, "ahp_cr": max(cr, 0.0)}  # tiny negative = rounding
        for m in METHODS:
            r = ranks_by_year(norm, w[m])
            stab, flips = [], 0
            for year in sorted(r["year"].unique()):
                a = full[m][full[m]["year"] == year].set_index("naics")
                b = r[r["year"] == year].set_index("naics").loc[a.index]
                stab.append(spearmanr(a["score"], b["score"])[0])
                if a["score"].idxmax() != b["score"].idxmax():
                    flips += 1
            pre = r[r["year"] == BASE_YEAR].set_index("naics")["score"]
            row[f"{m}_stability"] = sum(stab) / len(stab)
            row[f"{m}_top_flips"] = flips
            row[f"{m}_valid_rho"] = spearmanr(pre, drops.loc[pre.index])[0]
        rows.append(row)
    return pd.DataFrame(rows)


def main():
    table, summary = validate()
    os.makedirs(CLEAN_DIR, exist_ok=True)
    table.round(4).to_csv(OUT_FILE, index=False)
    summary.round(4).to_csv(OUT_SUMMARY, index=False)

    cols = ["naics", "industry", "drop_annual", "rank_actual"] + [f"rank_{m}" for m in METHODS]
    shown = table[cols].sort_values("rank_actual").copy()
    shown["drop_annual"] = (shown["drop_annual"] * 100).round(1).astype(str) + "%"
    print(f"Predicted risk ranks ({BASE_YEAR} scores) vs actual {SHOCK_YEAR} output drop "
          f"(rank 1 = riskiest / hardest hit):")
    print(shown.to_string(index=False))

    print("\nSpearman rank correlation with the actual 2020 drop:")
    print(summary.round(3).to_string(index=False))
    best = summary.iloc[0]
    print(f"\nBest predictor: {best['method'].upper()} "
          f"(rho = {best['spearman_annual']:.3f}, annual-average drop).")
    print("Note: with 6 industries, |rho| must be about 0.89+ to be significant at 5%.")
    print(f"Saved {OUT_FILE} and {OUT_SUMMARY}")

    by_year, by_ind = agreement()
    by_year.round(4).to_csv(OUT_AGREE_YEAR, index=False)
    by_ind.round(4).to_csv(OUT_AGREE_IND, index=False)
    print("\n=== Step 11: agreement between the three methods ===")
    print("Per year (Kendall's W: 1 = all three rank identically; rho = pairwise Spearman):")
    print(by_year.round(3).to_string(index=False))
    print("\nPer industry, across all 18 method-year rankings (rank 1 = riskiest):")
    print(by_ind.round(2).to_string(index=False))
    print(f"Saved {OUT_AGREE_YEAR} and {OUT_AGREE_IND}")

    sens = sensitivity()
    sens.round(4).to_csv(OUT_SENS, index=False)
    print("\n=== Step 12: sensitivity - drop one indicator at a time ===")
    table = pd.DataFrame({"dropped": sens["dropped"]})
    for m in METHODS:
        table[f"stab_{m}"] = sens[f"{m}_stability"]
    for m in METHODS:
        table[f"flips_{m}"] = sens[f"{m}_top_flips"]
    for m in METHODS:
        table[f"rho_{m}"] = sens[f"{m}_valid_rho"]
    print("stab  = mean Spearman vs the full ranking over 2019-2024 (1 = unchanged, low = that")
    print("        indicator was doing most of the work)")
    print("flips = years (of 6) where the #1 riskiest industry changes")
    print("rho   = Step 10 validation (2019 score vs actual 2020 output drop)\n")
    print(table.round(2).to_string(index=False))
    print()
    print(f"AHP consistency ratio after each drop: "
          + ", ".join(f"{d}={cr:.3f}" for d, cr in zip(sens["dropped"], sens["ahp_cr"])))
    print(f"Saved {OUT_SENS}")


if __name__ == "__main__":
    main()
