"""Supply Chain Risk Dashboard - Streamlit app.

Run from the project folder:
    streamlit run app.py

Needs data/clean/risk_indicators.csv (python -m src.build_dataset).
Live data needs EIA_KEY in .streamlit/secrets.toml (or Streamlit Cloud secrets).
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import INDUSTRIES, YEARS
from src.dashboard import LABELS, METHODS, comparison, contributions, load, scored, what_if
from globe_component import render_globe
from live_data import CHOKEPOINTS, PORTS, alert_level, live_signals
from live_panel import (alert_cards, crude_chart, industry_alert, product_strip, traffic_panel,
                        trend_chart)
from products import HORIZONS, REGIONS, product_label, products_for
from network import NODES, all_edges, find_alternatives, fmt_days, focus_for, hubs
from routes import SIGNAL_NAMES, filter_routes, is_exact, map_legend_html, route_map, route_table, route_table_html, signal_level
from risk_map import render_risk_map
from simulator import render_simulator
from ui_style import STATUS, apply_style, card_title, left_rail, pill, section, top_bar

# Colors: one fixed color per method (never re-assigned), neutral grey for context.
METHOD_COLORS = {"Equal": "#2a78d6", "Entropy": "#eb6834", "AHP": "#1baf7a"}
GREY = "#898781"
CLEAN = "data/clean"

st.set_page_config(page_title="Supply Chain Risk Pro", layout="wide", initial_sidebar_state="collapsed")
apply_style()


@st.cache_data
def data():
    return load()


df = data()

# ------------------------------- filter state -------------------------------
PRODUCTS = products_for(INDUSTRIES)
LABEL_TO_PRODUCT = {product_label(p): p for p in PRODUCTS}
DEFAULTS = {"f_product": product_label(PRODUCTS[0]), "f_search": "", "f_origin": "All Regions",
            "f_dest": "All Regions", "f_horizon": "Next 1–3 months"}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("method", list(METHODS)[0])
st.session_state.setdefault("year", max(YEARS))


def apply_search():
    q = st.session_state["f_search"].strip().lower()
    if q:
        hit = next((lab for lab, p in LABEL_TO_PRODUCT.items()
                    if q in lab.lower() or q in p["desc"].lower()), None)
        if hit:
            st.session_state["f_product"] = hit


def reset_filters():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v


product = LABEL_TO_PRODUCT[st.session_state["f_product"]]
naics = product["naics"]
industry = INDUSTRIES[naics]
method_name = st.session_state["method"]
method = METHODS[method_name]
year = st.session_state["year"]
table, weights = scored(df, method)
row = table[(table["naics"] == naics) & (table["year"] == year)].iloc[0]

# ------------------------------- live data + alert level -------------------------------
with st.spinner("Checking live sources..."):
    sig = live_signals()
latest = table[(table["naics"] == naics) & (table["year"] == max(YEARS))]
latest_score = float(latest["score"].iloc[0]) if not latest.empty else float(row["score"])
level, n_flags = alert_level(latest_score, sig)
o_sel, d_sel = st.session_state["f_origin"], st.session_state["f_dest"]
routes = filter_routes(o_sel, d_sel)
map_filtered = (o_sel, d_sel) != ("All Regions", "All Regions")
if not map_filtered:
    map_note = f"All routes · {len(routes)} lanes"
elif is_exact(o_sel, d_sel):
    map_note = f"{o_sel} ↔ {d_sel} · {len(routes)} route{'s' if len(routes) != 1 else ''}"
else:
    map_note = f"No direct lane {o_sel} ↔ {d_sel} · showing routes touching either region"
routes_df = route_table(sig, routes)
n_alerts = int(sig["weather"]["flag"]) + sum(
    1 for k in list(PORTS) + list(CHOKEPOINTS) if sig.get(k, {}).get("flag")) + int(
    sig["wti"]["flag"] or sig["gas"]["flag"] or sig["refinery"]["flag"])

left_rail(n_alerts)
top_bar(n_alerts, sig["checked_at"])

# ------------------------------- filter bar -------------------------------
st.markdown('<div id="filters" class="anchor"></div>', unsafe_allow_html=True)
with st.form("filters_form", border=False):
    c = st.columns([2.1, 2.1, 1.35, 1.35, 1.45, 0.75, 0.55], vertical_alignment="bottom")
    c[0].selectbox("HS Code or Product Code", list(LABEL_TO_PRODUCT), key="f_product",
                 help="Click and type to search, for example 2709 or crude.")
    c[1].text_input("Or search by product name", key="f_search", placeholder="Search product or HS code...")
    c[2].selectbox("Origin", REGIONS, key="f_origin")
    c[3].selectbox("Destination", REGIONS, key="f_dest")
    c[4].selectbox("Time Horizon", list(HORIZONS), key="f_horizon")
    c[5].form_submit_button("Apply", type="primary", width="stretch", on_click=apply_search)
    c[6].form_submit_button("Reset", width="stretch", on_click=reset_filters)

product_strip(product, sig, [r["name"] for r in routes])
alert_cards(sig)

# ------------------------------- map | traffic | routes -------------------------------
m, t, r = st.columns([1.3, 0.95, 1.1], gap="small")
with m:
    render_risk_map(sig, routes, routes_df, height=400, focus=map_filtered, note=map_note)
with t, st.container(border=True):
    card_title("Tanker Traffic")
    traffic_panel(sig)
with r, st.container(border=True):
    card_title("Route Risk &amp; Transit Time")
    st.markdown(route_table_html(routes_df), unsafe_allow_html=True)
    st.caption("Risk = warning signals on the route (0 Low, 1 Medium, 2+ High). Trend = tanker traffic at "
               "the route's weakest point. Transit times are typical, without port delays.")

# ------------------------------- simulator -------------------------------
st.markdown('<div id="simulator" class="anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    render_simulator(sig, level, HORIZONS[st.session_state["f_horizon"]])

# ------------------------------- trade & prices -------------------------------
section("prices", "Trade &amp; Prices", "Daily EIA spot prices and weekly Gulf Coast refinery use, "
        "up to the latest day each source has released.")
with st.container(border=True):
    rng = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366}
    pick = (st.segmented_control("Range", list(rng), default="3M", key="price_range")
            if hasattr(st, "segmented_control") else
            st.radio("Range", list(rng), index=1, horizontal=True, key="price_range")) or "3M"
    card_title("Crude Oil Benchmarks (WTI and Brent)")
    crude_chart(sig["series"], rng[pick])
a, b = st.columns(2)
with a, st.container(border=True):
    trend_chart(sig["series"]["gas"], "Henry Hub natural gas", "$/MMBtu", ".2f")
with b, st.container(border=True):
    trend_chart(sig["series"]["refinery"], "Gulf Coast refinery use", "%", ".1f",
                alert=85, alert_text="alert below 85%")

# ------------------------------- shipping & routes -------------------------------
section("shipping", "Shipping &amp; Routes", "All U.S. oil, gas and chemical corridors by ship, rail and "
        "truck. Pick a start and end point to see every alternative between them.")
ALL = "All U.S. routes"
hub_names = {v["name"]: k for k, v in NODES.items()}
f1, f2, f3 = st.columns([1.3, 1.3, 2.4], vertical_alignment="bottom")
g_from = f1.selectbox("From", [ALL] + list(hub_names), key="g_from")
g_to = f2.selectbox("To", [ALL] + list(hub_names), key="g_to")
alts = []
if g_from != ALL and g_to != ALL and g_from != g_to:
    alts = find_alternatives(hub_names[g_from], hub_names[g_to])
if alts:
    paths = [{"name": f"Option {n}: {a['label']} ({fmt_days(*a['days'])})", "mode": leg["mode"],
              "points": leg["points"]} for n, a in enumerate(alts, 1) for leg in a["legs"]]
    stops = sorted({s_ for a in alts for s_ in a["stops"]})
    globe_kw = dict(paths=paths, hubs=hubs(stops), focus=focus_for([p for x in paths for p in x["points"]]),
                    title=f"{g_from.split(' (')[0]} → {g_to.split(' (')[0]}: {len(alts)} route option(s)")
    f3.caption(f"Showing {len(alts)} alternative(s). Times are typical planning ranges, not quotes.")
else:
    globe_kw = dict(paths=all_edges(), hubs=hubs(), title="How U.S. oil, gas &amp; chemicals move")
    if g_from != ALL and g_to != ALL:
        f3.caption("No route found between these two points in the network." if g_from != g_to
                   else "Pick two different points.")
g, info = st.columns([1.3, 1], gap="small")
with g:
    render_globe(height=470, **globe_kw)
with info, st.container(border=True):
    if alts:
        card_title("Route alternatives", f"{g_from} → {g_to}")
        order = {"NODATA": 0, "NORMAL": 1, "MONITOR": 2, "ELEVATED": 3, "HIGH": 4}
        rows = ""
        for n, a in enumerate(alts, 1):
            lv = [signal_level(sig, k) for k in a["signals"]]
            worst = max(lv, key=lambda l: order[l]) if lv else "NORMAL"
            flagged = [SIGNAL_NAMES.get(k, k) for k in a["signals"] if signal_level(sig, k) == "HIGH"]
            risk_txt = {"HIGH": "High", "ELEVATED": "Medium", "MONITOR": "Monitor"}.get(worst, "Low")
            rows += (f"<tr><td><b>{n}</b></td><td>{a['label']}<br><span style='color:#64748B;font-size:12px'>"
                     f"{a['via']}</span></td><td class=num>{fmt_days(*a['days'])}</td>"
                     f"<td>{pill(worst, risk_txt)}"
                     + (f"<br><span style='color:#64748B;font-size:11.5px'>{', '.join(flagged)}</span>" if flagged else "")
                     + "</td></tr>")
        st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>#</th><th>Route</th>'
                    f'<th class=num>Transit (approx.)</th><th>Live risk</th></tr>{rows}</table></div>',
                    unsafe_allow_html=True)
        st.caption("Risk comes from live signals on each route (Gulf Coast weather, port and chokepoint "
                   "tanker traffic). Road and rail legs have no live feed yet.")
    else:
        card_title("Tanker traffic at key points", "7-day average vs the previous 90 days")
        rows = "".join(
            f"<tr><td>{v['label']}</td><td class=num>"
            f"{(format(sig[k]['value'], '+.0f') + '%') if sig[k]['value'] is not None else 'no data'}</td>"
            f"<td>{pill(signal_level(sig, k), STATUS[signal_level(sig, k)]['label'] if signal_level(sig, k) != 'NORMAL' else 'Normal')}</td>"
            f"<td>{format(sig[k]['date'], '%b %d') if sig[k]['date'] is not None else ''}</td></tr>"
            for k, v in {**PORTS, **CHOKEPOINTS}.items())
        st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>Place</th><th class=num>Change</th>'
                    f'<th>Status</th><th>Data through</th></tr>{rows}</table></div>', unsafe_allow_html=True)

# ------------------------------- risk & alerts -------------------------------
section("alerts", "Risk &amp; Alerts", "What changed, why it matters for your industry, and what to do.")
x, y = st.columns([1, 1.25], gap="small")
with x, st.container(border=True):
    industry_alert(industry, latest_score, sig, level)
with y, st.container(border=True):
    card_title("Active weather alerts (National Weather Service)",
               "Gulf Coast refinery and port counties in Texas and Louisiana")
    if sig["weather"]["detail"].empty:
        st.caption("No active alerts right now.")
    else:
        w = sig["weather"]["detail"].copy()
        if "supply_relevant" in w:
            w["supply_relevant"] = w["supply_relevant"].map({True: "yes", False: "no"})
        st.dataframe(w, width="stretch", hide_index=True, height=260)

with st.container(border=True):
    card_title(f"Structural risk: {industry}",
               f"Annual data {min(YEARS)}–{max(YEARS)} (the newest year the Census has published).")
    k1, k2 = st.columns([1, 2])
    k1.radio("Weighting method", list(METHODS), horizontal=True, key="method")
    k2.slider("Year (structural data)", min_value=min(YEARS), max_value=max(YEARS), step=1, key="year")
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


# ------------------------------- reports -------------------------------
section("reports", "Reports", "Model checks: validation, agreement between methods, sensitivity and backtest.")
# ------------------------------- model checks -------------------------------
with st.container(border=True):
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
