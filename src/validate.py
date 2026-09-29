"""Step 10: validation test - which weighting method predicted real disruption best?

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
from src.risk_index import build_scores, load_indicators

METHODS = ["equal", "entropy", "ahp"]
BASE_YEAR, SHOCK_YEAR = 2019, 2020
OUT_FILE = os.path.join(CLEAN_DIR, "validation.csv")
OUT_SUMMARY = os.path.join(CLEAN_DIR, "validation_summary.csv")


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


if __name__ == "__main__":
    main()
