"""
Procurement scenario simulator.

Uses the real latest crude price and its real past volatility to show a likely
price RANGE for orders placed now or 1-3 months from now. Freight and duties are
the user's own inputs. This is a statistical range, not a price forecast.
"""

import numpy as np
import pandas as pd
import streamlit as st

TRADING_DAYS_PER_MONTH = 21
BANDS = {"68% range (±1 standard deviation)": 1.0, "90% range": 1.645}


def daily_volatility(prices: pd.DataFrame, days: int = 250):
    s = prices.sort_values("date")["value"].astype(float).tail(days + 1)
    r = np.log(s).diff().dropna()
    return float(r.std()) if len(r) > 20 else None


def compute_scenarios(prices: pd.DataFrame, qty: float, freight: float, duties: float,
                      z: float, months=(0, 1, 2, 3)) -> tuple:
    """Return (table, info). Price range = latest × exp(±z · σ_daily · √trading days)."""
    if prices is None or prices.empty:
        return pd.DataFrame(), {}
    prices = prices.sort_values("date")
    last_price, last_date = float(prices["value"].iloc[-1]), pd.Timestamp(prices["date"].iloc[-1])
    sigma = daily_volatility(prices)
    if sigma is None:
        return pd.DataFrame(), {}
    today = pd.Timestamp.now(tz="America/Chicago").tz_localize(None).normalize()
    rows = []
    for m in months:
        spread = z * sigma * np.sqrt(TRADING_DAYS_PER_MONTH * m)
        lo, hi = last_price * np.exp(-spread), last_price * np.exp(spread)
        land_lo, land_hi = lo + freight + duties, hi + freight + duties
        rows.append({
            "Order date": (today + pd.DateOffset(months=m)).strftime("%b %d, %Y") + (" (now)" if m == 0 else ""),
            "Crude price ($/bbl)": f"{lo:,.2f}" if m == 0 else f"{lo:,.2f} – {hi:,.2f}",
            "Freight ($/bbl)": f"{freight:,.2f}",
            "Duties & fees ($/bbl)": f"{duties:,.2f}",
            "Landed cost ($/bbl)": f"{land_lo:,.2f}" if m == 0 else f"{land_lo:,.2f} – {land_hi:,.2f}",
            "Total cost ($)": f"{land_lo * qty / 1e6:,.2f}M" if m == 0
                              else f"{land_lo * qty / 1e6:,.2f}M – {land_hi * qty / 1e6:,.2f}M",
            "_lo": land_lo * qty, "_hi": land_hi * qty,
        })
    info = {"price": last_price, "date": last_date, "sigma": sigma,
            "annual_vol": sigma * np.sqrt(252) * 100}
    return pd.DataFrame(rows), info


def render_simulator(sig: dict, level: str) -> None:
    st.subheader("Procurement scenario simulator")
    st.caption("Uses the latest EIA crude price and its volatility over the past year. "
               "Freight and duties are your own inputs. The ranges show how far prices usually "
               "move over that time, not a forecast.")
    left, right = st.columns([1, 2.2], gap="large")
    with left, st.container(border=True):
        product = st.selectbox("Crude benchmark", ["WTI (U.S. Gulf / Cushing)", "Brent (international)"],
                               key="sim_product")
        qty = st.number_input("Quantity (barrels)", min_value=1_000, max_value=10_000_000,
                              value=100_000, step=10_000, key="sim_qty")
        freight = st.number_input("Freight ($/bbl, your quote)", min_value=0.0, max_value=50.0,
                                  value=3.0, step=0.25, key="sim_freight",
                                  help="Placeholder value. Enter the freight quote from your shipping broker.")
        duties = st.number_input("Duties & fees ($/bbl)", min_value=0.0, max_value=20.0,
                                 value=0.10, step=0.05, key="sim_duties")
        band = st.radio("Range", list(BANDS), key="sim_band")
    prices = sig["prices_full"]["wti" if product.startswith("WTI") else "brent"]
    table, info = compute_scenarios(prices, qty, freight, duties, BANDS[band])
    with right:
        if table.empty:
            st.info("Price data is not available right now, so the simulator cannot run.")
            return
        st.markdown(f"**Estimated landed cost scenarios** · latest price "
                    f"**${info['price']:,.2f}/bbl** on {info['date']:%b %d, %Y} · "
                    f"volatility {info['annual_vol']:.0f}% a year")
        st.dataframe(table.drop(columns=["_lo", "_hi"]), width="stretch", hide_index=True)
        now_cost = table["_lo"].iloc[0]
        last = table.iloc[-1]
        with st.container(border=True):
            st.markdown("**Key takeaways**")
            st.markdown(
                f"- Buying now locks in about **${now_cost / 1e6:,.2f}M** for {qty:,.0f} barrels.\n"
                f"- Waiting 3 months, the same order could cost between "
                f"**${(last['_lo'] - now_cost) / 1e6:+,.2f}M** and **${(last['_hi'] - now_cost) / 1e6:+,.2f}M** "
                f"compared with today ({band.split(' (')[0]}).\n"
                + ("- The live alert level is **HIGH**, so prices and freight may move faster than usual. "
                   "Consider securing part of the volume now." if level == "HIGH" else
                   "- The live alert level is not HIGH, so normal ordering is reasonable."))
