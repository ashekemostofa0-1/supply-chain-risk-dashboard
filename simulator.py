"""
Procurement scenario simulator: order now vs later, with landed-cost ranges.

Crude price ranges come from the latest EIA price and its real volatility over the past
year (a statistical range, not a forecast). Freight and duties are the user's own inputs,
because live tanker freight rates are only sold by paid services.
"""

import datetime as dt
import html

import numpy as np
import pandas as pd
import streamlit as st

from routes import ROUTES
from ui_style import card_title

TRADING_DAYS_PER_MONTH = 21
BBL_PER_TONNE = 7.33          # typical crude oil conversion
PORTS = {"Ras Tanura (SAU)": "Middle East", "Houston (USA)": "US Gulf Coast",
         "Port Arthur (USA)": "US Gulf Coast", "Corpus Christi (USA)": "US Gulf Coast",
         "Rotterdam (NLD)": "Europe", "Tokyo Bay (JPN)": "Northeast Asia", "Santos (BRA)": "South America"}


def daily_volatility(prices: pd.DataFrame, days: int = 250):
    s = prices.sort_values("date")["value"].astype(float).tail(days + 1)
    r = np.log(s).diff().dropna()
    return float(r.std()) if len(r) > 20 else None


def compute_scenarios(prices, start: dt.date, n_months: int, qty_bbl: float, freight: float, duties: float,
                      z: float = 1.0, freight_growth: float = 0.0):
    """Rows for start date + 0..n_months-1 months. Range = latest × exp(±z·σ·√trading days ahead)."""
    if prices is None or prices.empty:
        return pd.DataFrame(), {}
    prices = prices.sort_values("date")
    last_price, last_date = float(prices["value"].iloc[-1]), pd.Timestamp(prices["date"].iloc[-1])
    sigma = daily_volatility(prices)
    if sigma is None:
        return pd.DataFrame(), {}
    rows = []
    for m in range(n_months):
        when = pd.Timestamp(start) + pd.DateOffset(months=m)
        days_ahead = max((when - last_date).days, 0) * 252 / 365
        spread = z * sigma * np.sqrt(days_ahead)
        lo, hi = last_price * np.exp(-spread), last_price * np.exp(spread)
        fr = freight * (1 + freight_growth) ** m
        rows.append({"date": when, "qty": qty_bbl, "p_lo": lo, "p_hi": hi, "freight": fr, "duties": duties,
                     "l_lo": lo + fr + duties, "l_hi": hi + fr + duties,
                     "t_lo": (lo + fr + duties) * qty_bbl, "t_hi": (hi + fr + duties) * qty_bbl})
    return pd.DataFrame(rows), {"price": last_price, "date": last_date, "sigma": sigma,
                                "annual_vol": sigma * np.sqrt(252) * 100}


def _rng(a, b, fmt="{:,.1f}"):
    return fmt.format(a) if abs(b - a) < 0.05 else f"{fmt.format(a)} – {fmt.format(b)}"


def _money(x):
    return f"{x / 1e6:,.2f}M" if x >= 1e6 else f"{x / 1e3:,.0f}K"


def _transit(origin, dest):
    o, d = PORTS[origin], PORTS[dest]
    r = next((r for r in ROUTES if r["origin"] == o and r["dest"] == d), None)
    return r


def render_simulator(sig: dict, level: str, horizon_months: int) -> None:
    left, mid, right = st.columns([1, 2.15, 0.95], gap="medium")
    with left:
        card_title("Procurement Scenario Simulator")
        with st.form("sim"):
            a, b = st.columns(2)
            start = a.date_input("Order Date", value=dt.date.today(), key="sim_date")
            q1, q2 = b.columns([1.3, 1])
            qty = q1.number_input("Quantity", min_value=1_000, max_value=10_000_000, value=100_000,
                                  step=10_000, key="sim_qty")
            unit = q2.selectbox("Unit", ["Barrels (bbl)", "Metric tons (t)"], key="sim_unit")
            c, d = st.columns(2)
            origin = c.selectbox("Origin Port", list(PORTS), index=0, key="sim_origin")
            dest = d.selectbox("Destination Port", list(PORTS), index=1, key="sim_dest")
            e, f = st.columns(2)
            freight = e.number_input("Freight quote ($/bbl)", 0.0, 50.0, 3.0, 0.25, key="sim_freight",
                                     help="Your broker's quote. Live tanker freight rates are paid data.")
            sea = (sig.get("freight") or {}).get("modes", {}).get("sea", {})
            trend = sea.get("yoy")
            adjust = st.checkbox(
                f"Grow freight with the U.S. deep-sea freight trend ({trend:+.1f}% a year, BLS)"
                if trend is not None else "Grow freight with the deep-sea freight trend (no BLS data now)",
                value=trend is not None, disabled=trend is None, key="sim_adj")
            duties = f.number_input("Duties & fees ($/bbl)", 0.0, 20.0, 0.10, 0.05, key="sim_duties")
            st.form_submit_button("Run Scenarios", type="primary", width="stretch")
    qty_bbl = qty * (BBL_PER_TONNE if unit.startswith("Metric") else 1)
    bench = "wti" if PORTS[origin] == "US Gulf Coast" else "brent"
    monthly_growth = (1 + trend / 100) ** (1 / 12) - 1 if (adjust and trend is not None) else 0.0
    table, info = compute_scenarios(sig["prices_full"][bench], start, max(horizon_months, 3),
                                    qty_bbl, freight, duties, freight_growth=monthly_growth)
    route = _transit(origin, dest)
    with mid:
        card_title("Estimated Landed Cost Scenarios (USD)",
                   f"{'WTI' if bench == 'wti' else 'Brent'} price basis · "
                   + (f"latest ${info['price']:,.2f}/bbl on {info['date']:%b %d} · volatility "
                      f"{info['annual_vol']:.0f}%/yr" if info else "price data not available")
                   + (f" · voyage {route['typical']} ({html.escape(route['name'])})" if route else ""))
        if table.empty:
            st.info("Price data is not available right now, so the simulator cannot run.")
            return
        rows = "".join(
            f"<tr><td>{r.date:%b %d, %Y}</td><td class=num>{r.qty:,.0f}</td>"
            f"<td class=num>{_rng(r.p_lo, r.p_hi)}</td><td class=num>{r.freight:,.2f}</td>"
            f"<td class=num>{r.duties:,.2f}</td><td class=num>{_rng(r.l_lo, r.l_hi)}</td>"
            f"<td class=num>{_money(r.t_lo) if abs(r.t_hi - r.t_lo) < 1 else _money(r.t_lo) + ' – ' + _money(r.t_hi)}</td></tr>"
            for r in table.itertuples())
        st.markdown(
            '<div class="tbl-wrap"><table class="rt"><tr><th>Order Date</th><th class=num>Quantity (bbl)</th>'
            '<th class=num>Product Price (USD/bbl)</th><th class=num>Freight (USD/bbl)</th>'
            '<th class=num>Duties &amp; Fees (USD/bbl)</th><th class=num>Estimated Landed Cost (USD/bbl)</th>'
            f'<th class=num>Total Cost (USD)</th></tr>{rows}</table></div>', unsafe_allow_html=True)
        st.caption("Price ranges show about 2 in 3 likely outcomes (±1 standard deviation of past daily moves). "
                   "They are not a forecast.")
    with right:
        first, last = table.iloc[0], table.iloc[-1]
        mid_first = (first.t_lo + first.t_hi) / 2
        save_lo, save_hi = last.t_lo - mid_first, last.t_hi - mid_first
        items = [
            f"Ordering on {first.date:%b %d} costs about <b>${_money(mid_first)}</b> for {qty_bbl:,.0f} bbl.",
            f"Waiting until {last.date:%b %Y} could change the bill by <b>{_money(abs(save_lo))} less</b> "
            f"to <b>{_money(save_hi)} more</b>. The range widens the longer you wait.",
            ("Live alert is <b>HIGH</b>: prices and freight may move faster than usual. Consider securing part "
             "of the volume now." if level == "HIGH" else
             "Live alert is <b>ELEVATED</b>: split the order to spread price risk." if level == "ELEVATED" else
             "Live alert is <b>NORMAL</b>: regular ordering is reasonable."),
            "Freight starts from your quote" + (" and grows with the BLS deep-sea freight trend." if monthly_growth
             else ". Update it when your broker sends a new rate."),
        ]
        st.markdown('<div class="takeaways"><h4>💡 Key Takeaways</h4><ul style="padding-left:18px;margin:0">'
                    + "".join(f"<li>{i}</li>" for i in items) + "</ul></div>", unsafe_allow_html=True)
