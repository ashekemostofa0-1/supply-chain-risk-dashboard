"""Supply Chain Risk Dashboard - Streamlit app (Step 13).

Run from the project folder:
    streamlit run app.py

Needs data/clean/risk_indicators.csv (python -m src.build_dataset).
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import INDUSTRIES, YEARS
from src.dashboard import LABELS, METHODS, comparison, contributions, load, scored, what_if

# Colors: one fixed color per method (never re-assigned), neutral grey for context.
METHOD_COLORS = {"Equal": "#2a78d6", "Entropy": "#eb6834", "AHP": "#1baf7a"}
GREY = "#898781"
CLEAN = "data/clean"

st.set_page_config(page_title="Supply Chain Risk Dashboard", layout="wide")


@st.cache_data
def data():
    return load()


df = data()

# ------------------------------- sidebar -------------------------------
st.sidebar.header("Controls")
names = {f"{code} - {name}": code for code, name in INDUSTRIES.items()}
picked = st.sidebar.selectbox("Industry", list(names), index=1)
naics = names[picked]
year = st.sidebar.slider("Year", min_value=min(YEARS), max_value=max(YEARS), value=2020, step=1)
method_name = st.sidebar.radio("Weighting method", list(METHODS), index=0, horizontal=True)
method = METHODS[method_name]
st.sidebar.caption(
    "Scores run from 0 (lowest exposure in the 2019-2024 panel) to 1 (highest). "
    "Data: Census ASM / Economic Census / AIES, Census trade, FRED."
)

industry = INDUSTRIES[naics]
table, weights = scored(df, method)
row = table[(table["naics"] == naics) & (table["year"] == year)].iloc[0]

st.title("Supply Chain Risk Dashboard")
st.caption(f"U.S. chemical and plastics manufacturing, 6 industries (4-digit NAICS), 2019-2024. "
           f"Method: **{method_name}** weights.")

# ------------------------------- panel 1 -------------------------------
st.subheader(f"1. Risk score: {industry}, {year}")
c1, c2, c3 = st.columns(3)
prev = table[(table["naics"] == naics) & (table["year"] == year - 1)]
delta = None if prev.empty else f"{row['score'] - prev['score'].iloc[0]:+.3f} vs {year - 1}"
c1.metric("Risk score (0-1)", f"{row['score']:.3f}", delta, delta_color="inverse")
c2.metric("Rank this year", f"{row['rank']} of {len(INDUSTRIES)}", help="1 = riskiest")
flags = df[(df["naics"] == naics) & (df["year"] == year)]["flags"].fillna("").iloc[0]
c3.metric("Data source", df[(df["naics"] == naics) & (df["year"] == year)]["source"].iloc[0])
if flags:
    st.caption(f"Data note: {flags.replace(';', ', ').replace('_', ' ')}")

contrib = contributions(df, naics, year, method).sort_values("contribution")
fig1 = go.Figure(go.Bar(
    x=contrib["contribution"], y=contrib["indicator"], orientation="h",
    marker_color=METHOD_COLORS[method_name],
    text=[f"{v:.3f}" for v in contrib["contribution"]], textposition="outside",
    customdata=contrib[["normalized", "weight"]].to_numpy(),
    hovertemplate="<b>%{x:.3f}</b> %{y}<br>normalized %{customdata[0]:.3f} x weight "
                  "%{customdata[1]:.3f}<extra></extra>",
))
fig1.update_layout(height=260, margin=dict(l=10, r=40, t=30, b=10),
                   title="What drives the score (weight x normalized indicator)",
                   xaxis_title="Contribution to risk score", showlegend=False)
st.plotly_chart(fig1, width="stretch")

# ------------------------------- panel 2 -------------------------------
st.subheader(f"2. Risk over time: {industry}")
fig2 = go.Figure()
for name, m in METHODS.items():
    t, _ = scored(df, m)
    t = t[t["naics"] == naics].sort_values("year")
    chosen = name == method_name
    fig2.add_trace(go.Scatter(
        x=t["year"], y=t["score"], mode="lines+markers", name=name,
        line=dict(color=METHOD_COLORS[name], width=3 if chosen else 2, dash=None if chosen else "dot"),
        marker=dict(size=9 if chosen else 7),
        hovertemplate=f"<b>%{{y:.3f}}</b> {name}<extra></extra>",
    ))
fig2.add_vline(x=2020, line_dash="dash", line_color=GREY)
fig2.add_annotation(x=2020, y=1.02, yref="paper", text="2020 COVID shock", showarrow=False,
                    xanchor="left", font=dict(color=GREY))
fig2.add_vline(x=2022.5, line_dash="dot", line_color=GREY)
fig2.add_annotation(x=2022.5, y=0.02, yref="paper", text="survey change (AIES)", showarrow=False,
                    xanchor="left", font=dict(color=GREY, size=11))
fig2.update_layout(height=340, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified",
                   yaxis_title="Risk score", xaxis=dict(dtick=1),
                   legend=dict(orientation="h", y=1.12, x=0))
st.plotly_chart(fig2, width="stretch")

# ------------------------------- panel 3 -------------------------------
st.subheader(f"3. All industries, three methods side by side ({year})")
comp = comparison(df, year)
order = comp[comp["method"] == method_name].sort_values("score")["industry"].tolist()
fig3 = go.Figure()
for name in METHODS:
    t = comp[comp["method"] == name].set_index("industry").loc[order]
    fig3.add_trace(go.Bar(
        y=t.index, x=t["score"], name=name, orientation="h",
        marker_color=METHOD_COLORS[name],
        customdata=t["rank"], hovertemplate=f"<b>%{{x:.3f}}</b> {name}, rank %{{customdata}}<extra></extra>",
    ))
fig3.update_layout(barmode="group", bargap=0.25, bargroupgap=0.1, height=420,
                   margin=dict(l=10, r=10, t=10, b=10), xaxis_title="Risk score",
                   legend=dict(orientation="h", y=1.08, x=0))
st.plotly_chart(fig3, width="stretch")

ranks = comp.pivot(index="industry", columns="method", values="rank")[list(METHODS)]
ranks["Spread"] = ranks.max(axis=1) - ranks.min(axis=1)
ranks = ranks.sort_values(method_name)
st.caption("Rank under each method (1 = riskiest). Spread = how far the methods disagree.")
st.dataframe(ranks, width="stretch")

# ------------------------------- panel 4 -------------------------------
st.subheader("4. What if import dependence rises?")
w1, w2 = st.columns([2, 1])
pct = w1.slider("Raise import dependence by (%)", min_value=0, max_value=100, value=25, step=5)
scope = w2.radio("Apply to", [f"{industry} only", "All industries"], index=0)
res = what_if(df, method, year, pct, None if scope == "All industries" else naics)
sel = res[res["naics"] == naics].iloc[0]

m1, m2 = st.columns(2)
m1.metric(f"{industry}: score", f"{sel['score_after']:.3f}",
          f"{sel['score_after'] - sel['score_before']:+.3f}", delta_color="inverse")
m2.metric(f"{industry}: rank", f"{sel['rank_after']} of {len(INDUSTRIES)}",
          f"{int(sel['rank_change']):+d} places" if sel["rank_change"] else "no change",
          delta_color="inverse")

show = res[["industry", "score_before", "score_after", "rank_before", "rank_after"]].copy()
show.columns = ["Industry", "Score before", "Score after", "Rank before", "Rank after"]
st.dataframe(show.style.format({"Score before": "{:.3f}", "Score after": "{:.3f}"}),
             width="stretch", hide_index=True)
st.caption(f"Import dependence is multiplied by (1 + {pct}/100), capped at 100%, in {year}; "
           "all scores are then recalculated. Under Entropy the weights are also recalculated.")

# ------------------------------- model checks -------------------------------
with st.expander("Model checks (Steps 10-12)"):
    files = {"Validation vs 2020 output drop": "validation_summary.csv",
             "Agreement between methods, by industry": "agreement_by_industry.csv",
             "Sensitivity: drop one indicator": "sensitivity.csv"}
    for title, f in files.items():
        path = os.path.join(CLEAN, f)
        if os.path.exists(path):
            st.markdown(f"**{title}**")
            st.dataframe(pd.read_csv(path, dtype={"naics": str}).round(3), width="stretch",
                         hide_index=True)
        else:
            st.info(f"Run `python -m src.validate` to create {f}.")
