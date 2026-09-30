"""Supply Chain Early Warning & Procurement Intelligence - Streamlit app.

Run from the project folder:
    streamlit run app.py

Flow: product (HS) -> supplier country -> destination port -> risk index -> what changed ->
outlook and actions -> order now vs later -> alternative routes -> supplier comparison.
Needs data/clean/risk_indicators.csv (python -m src.build_dataset) and EIA_KEY, OILPRICE_KEY,
BLS_KEY in .streamlit/secrets.toml (or Streamlit Cloud secrets).
"""
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.config import INDUSTRIES, YEARS
from src.dashboard import LABELS, METHODS, comparison, contributions, load, scored, what_if
from decision import (evaluate_routes, level_of, render_changes, render_order_simulator,
                      render_outlook_actions, render_route_table, render_score_card, render_suppliers,
                      risk_components, combine, supplier_table, what_changed, LEVEL_WORD)
from globe_component import render_globe
from lanes import DESTS, ORIGINS, as_map_routes, FREIGHTOS_ERRORS
from live_data import CHOKEPOINTS, PORTS, alert_level, live_signals
from live_panel import (alert_cards, freight_panel, crude_chart, industry_alert, product_strip, traffic_panel,
                        trend_chart)
from products import HORIZONS, product_label, products_for
from network import NODES, all_edges, find_alternatives, fmt_days, focus_for, hubs
from routes import SIGNAL_NAMES, filter_routes, route_table, signal_level
from risk_map import render_risk_map
from ui_style import STATUS, apply_style, card_title, left_rail, pill, section, top_bar

# Colors: one fixed color per method (never re-assigned), neutral grey for context.
METHOD_COLORS = {"Equal": "#2a78d6", "Entropy": "#eb6834", "AHP": "#1baf7a"}
GREY = "#898781"
CLEAN = "data/clean"

st.set_page_config(page_title="Supply Chain Early Warning", layout="wide", initial_sidebar_state="collapsed")
apply_style()


@st.cache_data
def data():
    return load()


df = data()

# ------------------------------- filter state -------------------------------
PRODUCTS = products_for(INDUSTRIES)
LABEL_TO_PRODUCT = {product_label(p): p for p in PRODUCTS}
DEFAULT_PRODUCT = next((l for l, p in LABEL_TO_PRODUCT.items() if p["hs"] == "3901"), list(LABEL_TO_PRODUCT)[0])
DEFAULTS = {"f_product": DEFAULT_PRODUCT, "f_search": "", "f_dest": "Houston, TX",
            "f_horizon": "Next 1–3 months"}
for k, v in DEFAULTS.items():
    st.session_state.setdefault(k, v)
st.session_state.setdefault("f_supplier", LABEL_TO_PRODUCT[st.session_state["f_product"]]["origins"][0])
st.session_state.setdefault("method", list(METHODS)[0])
st.session_state.setdefault("year", max(YEARS))
st.session_state.setdefault("watchlist", [])


def on_product():
    p = LABEL_TO_PRODUCT[st.session_state["f_product"]]
    if st.session_state.get("f_supplier") not in p["origins"]:
        st.session_state["f_supplier"] = p["origins"][0]
    for k in ("sim_price", "sim_qty", "sim_route", "sup_prices", "sup_editor", "sim_quote", "sim_tariff",
              "sim_sens", "sim_payload"):
        st.session_state.pop(k, None)


def on_search():
    q = st.session_state["f_search"].strip().lower()
    if q:
        hit = next((lab for lab, p in LABEL_TO_PRODUCT.items()
                    if q in lab.lower() or q in p["desc"].lower() or q.replace(" ", "") in p["hs"]), None)
        if hit:
            st.session_state["f_product"] = hit
            on_product()


def reset_filters():
    for k, v in DEFAULTS.items():
        st.session_state[k] = v
    on_product()


product = LABEL_TO_PRODUCT[st.session_state["f_product"]]
if st.session_state["f_supplier"] not in product["origins"]:
    st.session_state["f_supplier"] = product["origins"][0]
origin, dest = st.session_state["f_supplier"], st.session_state["f_dest"]
naics = product["naics"]
industry = INDUSTRIES[naics]
method_name = st.session_state["method"]
method = METHODS[method_name]
year = st.session_state["year"]
table, weights = scored(df, method)
row = table[(table["naics"] == naics) & (table["year"] == year)].iloc[0]

# ------------------------------- live data -------------------------------
with st.spinner("Checking live sources..."):
    sig = live_signals()
latest = table[(table["naics"] == naics) & (table["year"] == max(YEARS))]
latest_score = float(latest["score"].iloc[0]) if not latest.empty else float(row["score"])
level, n_flags = alert_level(latest_score, sig)
n_alerts = int(sig["weather"]["flag"]) + sum(
    1 for k in list(PORTS) + list(CHOKEPOINTS) if sig.get(k, {}).get("flag")) + int(
    sig["wti"]["flag"] or sig["gas"]["flag"] or sig["refinery"]["flag"])

# ------------------------------- shipment inputs (defaults before widgets draw) -------------------------------
unit = product["unit"]
bench_last = sig["series"].get(product["benchmark"])
live_price = float(bench_last["value"].iloc[-1]) if bench_last is not None and len(bench_last) else None
default_qty = {"container": 500.0, "tanker": 100000.0, "bulk": 20000.0}[product["freight"]]
default_price = product["price"] if product["price"] else (live_price or 80.0)
wci = (sig.get("freight") or {}).get("market", {}).get("DREWRY_WCI_USD")
st.session_state.setdefault("sim_qty", default_qty)
st.session_state.setdefault("sim_price", float(default_price))
st.session_state.setdefault("sim_payload", float(product.get("payload", 20.0)))
st.session_state.setdefault("sim_box", float(round(wci["value"])) if wci else 4000.0)
st.session_state.setdefault("sim_quote", 3.0 if product["freight"] == "tanker" else 35.0)
st.session_state.setdefault("sim_tariff", 0.0 if product["hs"] == "2709" else 5.0)
st.session_state.setdefault("sim_allow", 5.0)
st.session_state.setdefault("sim_sens", 1.0 if product["hs"] in ("2709", "2710") else 0.5)
st.session_state.setdefault("w_cost", 0.4)
st.session_state.setdefault("w_time", 0.3)
st.session_state.setdefault("w_risk", 0.3)

routes_df, boxes = evaluate_routes(
    sig, product, origin, dest, latest_score, st.session_state["sim_qty"], st.session_state["sim_payload"],
    st.session_state["sim_box"], st.session_state["sim_quote"],
    st.session_state["w_cost"], st.session_state["w_time"], st.session_state["w_risk"])
best_key = routes_df.loc[routes_df["best"], "key"].iloc[0]
if st.session_state.get("sim_route") not in list(routes_df["key"]):
    st.session_state["sim_route"] = best_key
chosen = routes_df[routes_df["key"] == st.session_state["sim_route"]].iloc[0]

left_rail(n_alerts)
top_bar(n_alerts, sig["checked_at"])

# ------------------------------- ① filter bar -------------------------------
st.markdown('<div id="filters" class="anchor"></div>', unsafe_allow_html=True)
with st.container(border=True):
    c = st.columns([2.1, 1.8, 1.45, 1.5, 1.25, 0.65, 0.6], vertical_alignment="bottom")
    c[0].selectbox("① Product / HS code", list(LABEL_TO_PRODUCT), key="f_product", on_change=on_product,
                   help="Click and type to search, for example 3901 or polyethylene.")
    c[1].text_input("Or search product / HS code", key="f_search", on_change=on_search,
                    placeholder="e.g. polyethylene, 5503, crude")
    c[2].selectbox("② Supplier country", product["origins"], key="f_supplier")
    c[3].selectbox("Destination port", list(DESTS), key="f_dest")
    c[4].selectbox("Time horizon", list(HORIZONS), key="f_horizon")
    c[5].button("Apply", type="primary", on_click=on_search, width="stretch",
                help="Choices update instantly; Apply also runs the search box.")
    c[6].button("Reset", on_click=reset_filters, width="stretch")

lane_names = [f"Route {r.key}: {r.name}" for r in routes_df.itertuples()]
product_strip(product, sig, [f"{origin} ({ORIGINS[origin]['port']}) → {dest}"] + lane_names[:2])

# watchlist
w1, w2 = st.columns([1, 5], vertical_alignment="center")
if w1.button("☆ Add to watchlist", width="stretch"):
    item = (st.session_state["f_product"], origin, dest)
    if item not in st.session_state["watchlist"]:
        st.session_state["watchlist"].append(item)
if st.session_state["watchlist"]:
    chips = []
    for lab, o, d in st.session_state["watchlist"]:
        p = LABEL_TO_PRODUCT[lab]
        opts, _ = evaluate_routes(sig, p, o, d, latest_score, default_qty, p.get("payload", 20.0),
                                  st.session_state["sim_box"], st.session_state["sim_quote"])
        b = opts.loc[opts["best"]].iloc[0]
        sc = combine(risk_components(sig, p, o, d, b["option"], latest_score)[0])
        chips.append(pill(level_of(sc), f"HS {p['hs']} {p['name']} · {o} → {d.split(',')[0]} · {sc:.0f}"))
    w2.markdown("<div style='display:flex;gap:6px;flex-wrap:wrap'><b style='font-size:13px'>My watchlist:</b> "
                + " ".join(chips) + "</div>", unsafe_allow_html=True)
else:
    w2.caption("Add product + supplier + port combinations to monitor them side by side (kept for this browser "
               "session).")

# ------------------------------- ③ ④ ⑤ decision center -------------------------------
st.markdown('<div class="sect" id="decision">Supply Chain Risk Index</div>'
            f'<div class="csub">HS {product["hs"]} {product["name"]} · {origin} → {dest} · scored on '
            f'Route {chosen["key"]} ({chosen["name"]})</div>', unsafe_allow_html=True)
k1, k2, k3 = st.columns([1.05, 1.1, 1.15], gap="small")
with k2, st.container(border=True):
    card_title("④ What changed?")
    days = {"Since yesterday": 1, "Last 7 days": 7}[
        (st.segmented_control("Period", ["Since yesterday", "Last 7 days"], default="Last 7 days",
                              key="chg_period", label_visibility="collapsed")
         if hasattr(st, "segmented_control") else "Last 7 days") or "Last 7 days"]
    res = what_changed(sig, product, origin, dest, chosen["option"], latest_score, days)
    render_changes(res, days)
with k1, st.container(border=True):
    card_title("③ Live risk score", "0–100 for this product and lane · Low &lt; 45 · Medium 45–69 · High 70+")
    render_score_card(res)
with k3, st.container(border=True):
    card_title("⑤ What happens next & what to consider")
    render_outlook_actions(sig, product, res, origin, dest)

alert_cards(sig)

# ------------------------------- ⑥ order now vs later -------------------------------
st.markdown('<div id="simulator" class="anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="sect">⑥ Order now vs later</div><div class="csub">Estimated landed cost for your '
            'order at different dates. Your inputs + live prices, freight and risk.</div>', unsafe_allow_html=True)
with st.container(border=True):
    left, right = st.columns([1, 2.6], gap="medium")
    with left:
        a, b = st.columns(2)
        a.number_input(f"Quantity ({unit})", min_value=1.0, step=10.0 if unit == "t" else 1000.0, key="sim_qty")
        b.number_input(f"Price ($/{unit})", min_value=0.0, step=10.0 if unit == "t" else 1.0, key="sim_price",
                       help=("Starts at the live benchmark price." if product["price"] is None else
                             "Example value. Enter your supplier's quote."))
        if product["freight"] == "container":
            a, b = st.columns(2)
            a.number_input("Tons per 40ft box", min_value=1.0, max_value=30.0, step=1.0, key="sim_payload")
            b.number_input("Freight $ per 40ft", min_value=0.0, step=100.0, key="sim_box",
                           help="Used only if the Freightos estimate is unavailable. Default = Drewry World "
                                "Container Index (global average, not lane-specific).")
        else:
            st.number_input(f"Freight quote ($/{unit})", min_value=0.0, step=0.25, key="sim_quote",
                            help="Your broker's quote. Tanker and bulk rates are paid data.")
        a, b = st.columns(2)
        a.number_input("Tariff & fees (%)", min_value=0.0, max_value=100.0, step=0.5, key="sim_tariff",
                       help="Look up the rate for this HS code in the U.S. tariff schedule (hts.usitc.gov).")
        b.number_input("Max risk allowance (%)", min_value=0.0, max_value=30.0, step=0.5, key="sim_allow",
                       help="Budget for delays and expediting at a risk score of 100.")
        st.selectbox("Route", list(routes_df["key"]), key="sim_route",
                     format_func=lambda k: f"Route {k}: " + routes_df.set_index("key").loc[k, "name"])
        st.slider("Price sensitivity to benchmark", 0.0, 1.5, step=0.1, key="sim_sens",
                  help="1.0 = moves like the benchmark (crude). Lower for resins and fibers (assumption).")
        grow = st.checkbox("Grow freight with the BLS freight trend", value=True, key="sim_grow")
    with right:
        render_order_simulator(sig, product, origin, dest, routes_df, boxes, res["now"],
                               st.session_state["sim_qty"], st.session_state["sim_price"],
                               st.session_state["sim_tariff"], st.session_state["sim_allow"], grow,
                               st.session_state["sim_route"], st.session_state["sim_sens"])
        if product["freight"] == "container":
            est = routes_df.loc[routes_df["key"] == "A", "est"].iloc[0]
            if est:
                st.caption(f"Freight for Route A: Freightos estimate for {boxes} × 40ft "
                           f"({est['mode']}, {est['t_min']:.0f}–{est['t_max']:.0f} days). Other routes are scaled "
                           "scenarios. [Freight estimates by Freightos](https://www.freightos.com)")
            else:
                st.caption(f"Freight = ${st.session_state['sim_box']:,.0f} per 40ft × {boxes} boxes. Default is the "
                           "Drewry World Container Index (weekly global average, via OilPriceAPI), not a lane quote. "
                           "Enter your forwarder's quote in 'Fallback $ per 40ft' for a lane-specific cost. "
                           "(The free Freightos estimate currently returns no carrier quotes for these lanes.)")

# ------------------------------- ⑦ alternative routes + map -------------------------------
st.markdown('<div id="routes" class="anchor"></div>', unsafe_allow_html=True)
st.markdown('<div class="sect">⑦ Alternative routes & suppliers</div><div class="csub">Compare by cost, transit time '
            'and live disruption risk. Route costs other than the Freightos lane are estimated scenarios.</div>',
            unsafe_allow_html=True)
m, rt = st.columns([1.15, 1.25], gap="small")
with m:
    all_lanes = st.toggle("Show all main lanes", value=False, key="map_all")
    if all_lanes:
        map_routes = filter_routes("All Regions", "All Regions")
        note = f"All main lanes · {len(map_routes)}"
    else:
        map_routes = as_map_routes(origin, dest, [r.option for r in routes_df.itertuples()])
        note = f"{origin} → {dest.split(',')[0]} · {len(map_routes)} route option(s)"
    render_risk_map(sig, map_routes, route_table(sig, map_routes), height=420, focus=not all_lanes, note=note)
with rt, st.container(border=True):
    card_title("Route comparison", f"{origin} ({ORIGINS[origin]['port']}) → {dest}")
    render_route_table(routes_df, product)
    with st.expander("Change what 'best balance' means"):
        x, y, z = st.columns(3)
        x.slider("Cost weight", 0.0, 1.0, step=0.1, key="w_cost")
        y.slider("Time weight", 0.0, 1.0, step=0.1, key="w_time")
        z.slider("Risk weight", 0.0, 1.0, step=0.1, key="w_risk")
    b = routes_df.loc[routes_df["best"]].iloc[0]
    st.markdown(f"**Best balance: Route {b['key']}**, not only because of cost: it has the best mix of cost, "
                f"{b['days'][0]}–{b['days'][1]} days transit and route risk {b['risk']:.0f}/100 with your weights.")

with st.container(border=True):
    card_title(f"Supplier comparison: HS {product['hs']} {product['name']} → {dest}",
               "Edit prices to match your quotes. Overall = 40% landed cost, 30% lead time, 30% risk (lower = better).")
    st.session_state.setdefault("sup_prices", {c: float(st.session_state["sim_price"]) for c in product["origins"]})
    ed = st.data_editor(pd.DataFrame({"Supplier country": list(st.session_state["sup_prices"]),
                                      f"Price ($/{unit})": list(st.session_state["sup_prices"].values())}),
                        hide_index=True, disabled=["Supplier country"], key="sup_editor", width="stretch")
    prices = dict(zip(ed["Supplier country"], ed[f"Price ($/{unit})"]))
    sdf = supplier_table(sig, product, dest, latest_score, st.session_state["sim_qty"],
                         st.session_state["sim_payload"], st.session_state["sim_box"], st.session_state["sim_quote"],
                         prices, st.session_state["sim_tariff"], st.session_state["sim_allow"])
    render_suppliers(sdf, product)
    st.caption("Lead time = transit on each supplier's best route (production time not included). Risk uses the "
               "same live index. Mexico is overland, so it avoids ocean chokepoints.")


# ------------------------------- more detail below -------------------------------
# ------------------------------- trade & prices -------------------------------
section("prices", "Prices &amp; Freight", "Daily EIA spot prices and weekly Gulf Coast refinery use, "
        "up to the latest day each source has released.")
with st.container(border=True):
    rng = {"1M": 31, "3M": 92, "6M": 183, "1Y": 366}
    pick = (st.segmented_control("Range", list(rng), default="3M", key="price_range")
            if hasattr(st, "segmented_control") else
            st.radio("Range", list(rng), index=1, horizontal=True, key="price_range")) or "3M"
    card_title("Crude Oil Benchmarks (WTI and Brent)")
    crude_chart(sig["series"], rng[pick])
with st.container(border=True):
    card_title("Freight Market", "Free official freight price indexes by mode (U.S. BLS, monthly) "
               "and global shipping indexes (OilPriceAPI free tier)")
    freight_panel(sig["freight"])
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

t1, t2 = st.columns([1, 1.25], gap="small")
with t1, st.container(border=True):
    card_title("Tanker Traffic")
    traffic_panel(sig)
with t2, st.container(border=True):
    card_title("Live signals behind the risk index", "Current value and status of every live signal")
    rows = "".join(
        f"<tr><td>{v['label']}</td><td class=num>"
        f"{(format(sig[k]['value'], '+.0f') + '%') if sig[k]['value'] is not None else 'no data'}</td>"
        f"<td>{pill(signal_level(sig, k))}</td></tr>" for k, v in {**PORTS, **CHOKEPOINTS}.items())
    st.markdown('<div class="tbl-wrap"><table class="rt"><tr><th>Place (tanker traffic 7d vs 90d)</th>'
                f'<th class=num>Change</th><th>Status</th></tr>{rows}</table></div>', unsafe_allow_html=True)

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
