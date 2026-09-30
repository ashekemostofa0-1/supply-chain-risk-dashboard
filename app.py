"""Supply Chain Risk Dashboard - Streamlit app.

Run from the project folder:
    streamlit run app.py

Needs data/clean/risk_indicators.csv (python -m src.build_dataset).
Live data needs EIA_KEY in .streamlit/secrets.toml (or Streamlit Cloud secrets).
"""
import html
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import INDUSTRIES, YEARS
from src.dashboard import LABELS, METHODS, comparison, contributions, load, scored, what_if
from globe_component import render_globe
from live_data import CHOKEPOINTS, PORTS, alert_level, live_signals
from live_panel import alert_cards, crude_chart, industry_alert, trend_chart
from routes import route_map, route_table
from simulator import render_simulator
from ui_style import STATUS, apply_style, brand_bar, pill, section

# Colors: one fixed color per method (never re-assigned), neutral grey for context.
METHOD_COLORS = {"Equal": "#2a78d6", "Entropy": "#eb6834", "AHP": "#1baf7a"}
GREY = "#898781"
CLEAN = "data/clean"

st.set_page_config(page_title="Supply Chain Risk Dashboard", layout="wide")
apply_style()


@st.cache_data
def data():
    return load()


df = data()

# ------------------------------- sidebar -------------------------------
st.sidebar.header("Controls")
names = {f"{code} - {name}": code for code, name in INDUSTRIES.items()}
picked = st.sidebar.selectbox("Industry", list(names), index=1)
naics = names[picked]
year = st.sidebar.slider("Year (structural data)", min_value=min(YEARS), max_value=max(YEARS),
                         value=max(YEARS), step=1)
method_name = st.sidebar.radio("Weighting method", list(METHODS), index=0, horizontal=True)
method = METHODS[method_name]
if st.sidebar.button("Refresh live data", width="stretch"):
    st.cache_data.clear()
    st.rerun()
st.sidebar.caption(
    f"Structural scores run from 0 (lowest exposure in the {min(YEARS)}-{max(YEARS)} panel) to 1 "
    "(highest). Data: Census ASM / Economic Census / AIES, Census trade, FRED. "
    "Live signals: National Weather Service, EIA, IMF PortWatch."
)

industry = INDUSTRIES[naics]
table, weights = scored(df, method)
row = table[(table["naics"] == naics) & (table["year"] == year)].iloc[0]

# ------------------------------- live data + alert level -------------------------------
with st.spinner("Checking live sources..."):
    sig = live_signals()
# The live alert uses the most recent structural score, not the year on the slider.
latest = table[(table["naics"] == naics) & (table["year"] == max(YEARS))]
latest_score = float(latest["score"].iloc[0]) if not latest.empty else float(row["score"])
level, n_flags = alert_level(latest_score, sig)
routes_df = route_table(sig)

brand_bar(
    "Supply Chain Risk Dashboard",
    "Oil, gas & chemical supply risk for U.S. Gulf Coast manufacturing",
    pill(level, f"{industry}: {STATUS[level]['label']}")
    + f'<span class="meta">Live data checked {html.escape(sig["checked_at"])}<br>'
      f'Structural data {min(YEARS)}–{max(YEARS)} · Method: {html.escape(method_name)}</span>')
st.write("")

tab_over, tab_ind, tab_prices, tab_ship, tab_sim = st.tabs(
    ["Overview", "Industry Risk", "Prices & Trends", "Shipping & Routes", "Procurement Simulator"])

# ================================ OVERVIEW ================================
with tab_over:
    alert_cards(sig)
    if not sig["weather"]["detail"].empty:
        with st.expander("Active weather alerts (National Weather Service)"):
            show_w = sig["weather"]["detail"].copy()
            show_w["supply_relevant"] = show_w["supply_relevant"].map({True: "yes", False: "no"})
            st.dataframe(show_w, width="stretch", hide_index=True)
    st.write("")
    m, t = st.columns([1.55, 1], gap="large")
    with m, st.container(border=True):
        section("Global route risk map",
                "Main tanker lanes for U.S. Gulf Coast oil and chemicals. Colors come from live signals.")
        st.plotly_chart(route_map(sig, routes_df), width="stretch", config={"displayModeBar": False})
        st.caption("Routes are illustrative major lanes, not scaled to volume.")
    with t, st.container(border=True):
        section("Your industry right now")
        industry_alert(industry, latest_score, sig, level)
    with st.container(border=True):
        section("Route risk and transit time",
                "Risk = number of warning signals on the route: 0 Normal, 1 Elevated, 2+ High.")
        show = routes_df.copy()
        show["Risk"] = show["Risk"].map(lambda l: f"{STATUS[l]['icon']} {STATUS[l]['label']}")
        st.dataframe(show, width="stretch", hide_index=True)
        st.caption("Voyage times are approximate for a tanker at about 12-13 knots, without port delays. "
                   "Traffic data: IMF PortWatch (2 to 4 days behind).")

# ================================ PRICES ================================
with tab_prices:
    with st.container(border=True):
        section("Crude oil benchmarks", "Daily spot prices from the EIA.")
        rng = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366}
        if hasattr(st, "segmented_control"):
            pick = st.segmented_control("Range", list(rng), default="3M", key="price_range") or "3M"
        else:
            pick = st.radio("Range", list(rng), index=1, horizontal=True, key="price_range")
        crude_chart(sig["series"], rng[pick])
    a, b = st.columns(2)
    with a, st.container(border=True):
        trend_chart(sig["series"]["gas"], "Henry Hub natural gas", "$/MMBtu", ".2f")
    with b, st.container(border=True):
        trend_chart(sig["series"]["refinery"], "Gulf Coast refinery use", "%", ".1f",
                    alert=85, alert_text="alert below 85%")
    st.caption("Structural scores use annual data (latest year 2024, the newest the Census has published). "
               "Live signals and these charts run up to the latest day each source has released.")

# ================================ SHIPPING ================================
with tab_ship:
    g, info = st.columns([1.3, 1], gap="large")
    with g:
        render_globe(height=500)
    with info, st.container(border=True):
        section("Tanker traffic at key points", "7-day average vs the previous 90 days (IMF PortWatch).")
        places = {**PORTS, **CHOKEPOINTS}
        rows = [{"Place": v["label"],
                 "Change": f"{sig[k]['value']:+.0f}%" if sig[k]["value"] is not None else "no data",
                 "Status": f"{STATUS[s]['icon']} {STATUS[s]['label']}",
                 "Data through": f"{sig[k]['date']:%b %d}" if sig[k]["date"] is not None else ""}
                for k, v in places.items()
                for s in [("HIGH" if sig[k].get("flag") else "NODATA" if sig[k]["value"] is None
                           else "MONITOR" if sig[k]["value"] <= -10 else "NORMAL")]]
        st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    cols = st.columns(3)
    for i, (k, v) in enumerate({**PORTS, **CHOKEPOINTS}.items()):
        with cols[i % 3], st.container(border=True):
            trend_chart(sig["series"].get(k), f"{v['label']}, tanker calls or transits (7-day avg)",
                        "per day", ".1f", height=210)

# ================================ SIMULATOR ================================
with tab_sim:
    render_simulator(sig, level)

# ================================ INDUSTRY RISK ================================
with tab_ind:
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
    # Plotly stacks horizontal group bars bottom-up, so add them in reverse to read
    # Equal / Entropy / AHP from top to bottom, matching the legend (legendrank keeps its order).
    for i, name in enumerate(reversed(list(METHODS))):
        t = comp[comp["method"] == name].set_index("industry").loc[order]
        fig3.add_trace(go.Bar(
            y=t.index, x=t["score"], name=name, orientation="h", legendrank=3 - i,
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
    d_score = sel["score_after"] - sel["score_before"]
    d_rank = int(sel["rank_change"])
    # Streamlit draws an up-arrow for any non-negative delta, so show no delta when nothing moved.
    m1.metric(f"{industry}: score", f"{sel['score_after']:.3f}",
              f"{d_score:+.3f}" if abs(d_score) >= 0.0005 else None, delta_color="inverse")
    m2.metric(f"{industry}: rank", f"{sel['rank_after']} of {len(INDUSTRIES)}",
              f"{'up' if d_rank > 0 else 'down'} {abs(d_rank)} place{'s' if abs(d_rank) > 1 else ''}"
              if d_rank else None,
              delta_color="inverse" if d_rank > 0 else "normal")
    if not d_rank:
        m2.caption("No change in rank")

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
                 "Sensitivity: drop one indicator": "sensitivity.csv",
                 "Backtest of live alert rules (python backtest.py)": "backtest_summary.csv"}
        for title, f in files.items():
            path = os.path.join(CLEAN, f)
            if os.path.exists(path):
                st.markdown(f"**{title}**")
                st.dataframe(pd.read_csv(path, dtype={"naics": str}).round(3), width="stretch",
                             hide_index=True)
            else:
                st.info(f"Run `python -m src.validate` to create {f}.")
