"""
Free freight data for the dashboard.

1. U.S. BLS Producer Price Indexes (monthly, official, free):
      PCU483111483111  Deep sea freight transportation
      PCU484121484121  General freight trucking, long-distance truckload
      PCU482111482111  Line-haul railroads
   Works without a key (BLS API v1, 25 calls/day); a free key (BLS_KEY) raises the limit.
2. OilPriceAPI free tier (latest value only, 50 calls/day, key OILPRICE_KEY):
      BALTIC_DRY_INDEX  (daily, dry bulk ships)
      DREWRY_WCI_USD    (weekly, containers, USD per 40ft box)

Live tanker rates (VLCC, Suezmax...) are paid data, so they are NOT here. These free
indexes show general freight cost pressure by mode.
"""

import datetime as dt

import pandas as pd
import requests
import streamlit as st

BLS_SERIES = {"sea": ("PCU483111483111", "Deep-sea freight"),
              "truck": ("PCU484121484121", "Truck (long-distance)"),
              "rail": ("PCU482111482111", "Rail (line-haul)")}
MARKET_CODES = {"BALTIC_DRY_INDEX": ("Baltic Dry Index", "points", "dry bulk ships, daily"),
                "DREWRY_WCI_USD": ("Drewry World Container Index", "USD / 40ft", "containers, weekly")}
ERRORS = {}


def _secret(name):
    try:
        return st.secrets.get(name)
    except Exception:
        return None


@st.cache_data(ttl=12 * 3600, show_spinner=False)
def _bls(key):
    year = dt.date.today().year
    body = {"seriesid": [s for s, _ in BLS_SERIES.values()], "startyear": str(year - 3), "endyear": str(year)}
    url = "https://api.bls.gov/publicAPI/v1/timeseries/data/"
    if key:
        body["registrationkey"] = key
        url = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
    r = requests.post(url, json=body, timeout=30)
    r.raise_for_status()
    js = r.json()
    if js.get("status") != "REQUEST_SUCCEEDED":
        raise ValueError(" ".join(js.get("message", [])) or js.get("status"))
    rows = []
    back = {s: k for k, (s, _) in BLS_SERIES.items()}
    for ser in js["Results"]["series"]:
        for d in ser["data"]:
            if not d["period"].startswith("M") or d["period"] == "M13":
                continue
            rows.append({"mode": back[ser["seriesID"]],
                         "date": pd.Timestamp(int(d["year"]), int(d["period"][1:]), 1),
                         "value": float(d["value"])})
    if not rows:
        raise ValueError("no data")
    return pd.DataFrame(rows).sort_values(["mode", "date"])


def bls_freight() -> pd.DataFrame:
    """Monthly PPI for sea, truck and rail freight. Empty frame on failure."""
    try:
        return _bls(_secret("BLS_KEY"))
    except Exception as e:
        ERRORS["BLS"] = repr(e)[:200]
        return pd.DataFrame(columns=["mode", "date", "value"])


def yoy(df: pd.DataFrame, mode: str):
    """Latest value, % change vs 12 months earlier, latest month."""
    d = df[df["mode"] == mode].set_index("date")["value"]
    if len(d) < 13:
        return None, None, None
    last_date = d.index[-1]
    prev = d.get(last_date - pd.DateOffset(years=1))
    return d.iloc[-1], (None if prev is None else (d.iloc[-1] / prev - 1) * 100), last_date


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def _oilprice(code, key):
    r = requests.get("https://api.oilpriceapi.com/v1/prices/latest", params={"by_code": code},
                     headers={"Authorization": f"Token {key}", "Content-Type": "application/json"}, timeout=20)
    r.raise_for_status()
    d = r.json().get("data") or {}
    price = d.get("price", d.get("value"))
    if price is None:
        raise ValueError("no price in response")
    return {"value": float(price), "date": str(d.get("created_at") or d.get("updated_at") or "")[:10]}


def market_indexes() -> dict:
    """Latest Baltic Dry and Drewry container index. {} if no key or failure."""
    key = _secret("OILPRICE_KEY")
    if not key:
        ERRORS["OilPriceAPI"] = "OILPRICE_KEY missing from secrets"
        return {}
    out = {}
    for code in MARKET_CODES:
        try:
            out[code] = _oilprice(code, key)
        except Exception as e:
            ERRORS[f"OilPriceAPI {code}"] = repr(e)[:200]
    return out


def freight_signals() -> dict:
    df = bls_freight()
    modes = {}
    for m in BLS_SERIES:
        v, ch, when = yoy(df, m) if not df.empty else (None, None, None)
        modes[m] = {"value": v, "yoy": ch, "date": when}
    return {"bls": df, "modes": modes, "market": market_indexes()}
