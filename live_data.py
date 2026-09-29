"""
Live and daily data for the Supply Chain Risk Dashboard.

Sources (all free):
  - NWS alerts (api.weather.gov)      -> real time, no key
  - FRED daily prices (fredgraph.csv) -> daily, no key
  - EIA weekly refinery utilization   -> weekly, free key (st.secrets["EIA_KEY"])
  - IMF PortWatch daily port calls     -> daily values, no key

Every function is cached with a time-to-live (ttl), so the app does not call the
APIs on every click. Every function returns an empty result instead of crashing
if a source is down, so the demo keeps working.
"""

import io
import datetime as dt
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

LAST_ERRORS = {}   # why a source failed (shown by check_sources.py)

HEADERS = {"User-Agent": "(SupplyChainRiskDashboard, Lamar University student project)"}

# Gulf Coast counties / parishes that matter for oil, gas and chemicals
GULF_AREAS = ["Jefferson", "Orange", "Hardin", "Harris", "Galveston", "Brazoria",
              "Chambers", "Nueces", "San Patricio", "Calcasieu", "Cameron"]


# ---------------------------------------------------------------- REAL TIME
@st.cache_data(ttl=600, show_spinner=False)          # refresh every 10 minutes
def nws_alerts(states=("TX", "LA")) -> pd.DataFrame:
    """Active weather alerts in Gulf Coast counties (hurricane, flood, freeze...)."""
    rows = []
    for s in states:
        try:
            r = requests.get("https://api.weather.gov/alerts/active",
                             params={"area": s}, headers=HEADERS, timeout=20)
            r.raise_for_status()
            for f in r.json().get("features", []):
                p = f.get("properties", {})
                area = p.get("areaDesc", "") or ""
                if any(a in area for a in GULF_AREAS):
                    rows.append({"event": p.get("event"), "severity": p.get("severity"),
                                 "area": area, "headline": p.get("headline"),
                                 "expires": p.get("expires")})
        except Exception:
            continue
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- DAILY
@st.cache_data(ttl=6 * 3600, show_spinner=False)     # refresh every 6 hours
def _fred_daily(series_id: str) -> pd.DataFrame:
    """Daily series from FRED without an API key.
    DCOILWTICO = WTI crude ($/bbl), DHHNGSP = Henry Hub natural gas ($/MMBtu)."""
    try:
        r = requests.get("https://fred.stlouisfed.org/graph/fredgraph.csv",
                         params={"id": series_id},
                         headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
                         timeout=15)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))
        df.columns = ["date", "value"]
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().tail(400)
        if df.empty:
            raise ValueError("empty")
        return df
    except Exception as e:
        LAST_ERRORS[f"FRED {series_id}"] = repr(e)[:200]
        raise   # failures are NOT cached, so the next page load tries again


def fred_daily(series_id: str) -> pd.DataFrame:
    try:
        return _fred_daily(series_id)
    except Exception:
        return pd.DataFrame(columns=["date", "value"])


PORTWATCH = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services"


@st.cache_data(ttl=12 * 3600, show_spinner=False)    # refresh twice a day
def _portwatch_daily(service: str, name_like: str, n: int = 200) -> pd.DataFrame:
    """Daily port calls (Daily_Ports_Data) or chokepoint transits
    (Daily_Chokepoints_Data) from IMF PortWatch."""
    try:
        r = requests.get(f"{PORTWATCH}/{service}/FeatureServer/0/query",
                         params={"where": f"portname LIKE '%{name_like}%'",
                                 "outFields": "*", "orderByFields": "date DESC",
                                 "resultRecordCount": n, "f": "json"},
                         timeout=30)
        r.raise_for_status()
        df = pd.DataFrame([f["attributes"] for f in r.json().get("features", [])])
        if df.empty:
            raise ValueError("no rows")
        # PortWatch dates may come as text or as milliseconds since 1970
        if pd.api.types.is_numeric_dtype(df["date"]):
            df["date"] = pd.to_datetime(df["date"], unit="ms")
        else:
            df["date"] = pd.to_datetime(df["date"])
        return df.sort_values("date")
    except Exception as e:
        LAST_ERRORS[f"PortWatch {name_like}"] = repr(e)[:200]
        raise


def portwatch_daily(service: str, name_like: str, n: int = 200) -> pd.DataFrame:
    try:
        return _portwatch_daily(service, name_like, n)
    except Exception:
        return pd.DataFrame()


def tanker_column(df: pd.DataFrame):
    """Find the tanker-count column (check df.columns once and hard-code it if needed)."""
    cands = [c for c in df.columns if "tanker" in c.lower()]
    calls = [c for c in cands if c.lower().startswith(("n_", "portcalls", "n_total")) or "call" in c.lower()]
    return (calls or cands or [None])[0]


# ---------------------------------------------------------------- WEEKLY
@st.cache_data(ttl=24 * 3600, show_spinner=False)    # refresh once a day
def _eia_series(series_id: str, keep: int, key: str) -> pd.DataFrame:
    """Any EIA series. Default: Gulf Coast (PADD 3) weekly refinery utilization, %.
    Daily prices: PET.RWTC.D = WTI crude spot, NG.RNGWHHD.D = Henry Hub gas spot.
    Needs a free key from eia.gov/opendata saved as EIA_KEY in Streamlit secrets."""
    try:
        r = requests.get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                         params={"api_key": key}, timeout=30)
        r.raise_for_status()
        data = r.json()["response"]["data"]
        df = pd.DataFrame(data)[["period", "value"]].rename(columns={"period": "date"})
        df["date"] = pd.to_datetime(df["date"])
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df = df.dropna().sort_values("date").tail(keep)
        if df.empty:
            raise ValueError("empty")
        return df
    except Exception as e:
        LAST_ERRORS[f"EIA {series_id}"] = repr(e)[:200]
        raise


def eia_series(series_id: str = "PET.W_NA_YUP_R30_PER.W", keep: int = 400) -> pd.DataFrame:
    """Any EIA series. Default: Gulf Coast (PADD 3) weekly refinery utilization, %.
    Daily prices: PET.RWTC.D = WTI crude spot, NG.RNGWHHD.D = Henry Hub gas spot.
    Needs a free key from eia.gov/opendata saved as EIA_KEY in Streamlit secrets."""
    try:
        key = st.secrets.get("EIA_KEY", None)
    except Exception:          # no secrets file yet
        key = None
    if not key:
        LAST_ERRORS["EIA"] = "EIA_KEY missing from secrets"
        return pd.DataFrame(columns=["date", "value"])
    try:
        return _eia_series(series_id, keep, key)
    except Exception:
        return pd.DataFrame(columns=["date", "value"])


def eia_weekly():
    return eia_series("PET.W_NA_YUP_R30_PER.W", keep=104)


def daily_price(name: str) -> pd.DataFrame:
    """WTI or Henry Hub daily price: EIA first (needs key), FRED as backup."""
    eia_id, fred_id = {"wti": ("PET.RWTC.D", "DCOILWTICO"),
                       "gas": ("NG.RNGWHHD.D", "DHHNGSP")}[name]
    df = eia_series(eia_id)
    return df if len(df) else fred_daily(fred_id)


# ---------------------------------------------------------------- SIGNALS
def pct_change(df: pd.DataFrame, col: str = "value", recent: int = 5, base: int = 60):
    """Recent average vs. baseline average, in percent. None if not enough data."""
    if df is None or df.empty or col not in df or len(df) < recent + base:
        return None
    s = df[col].astype(float)
    now, before = s.tail(recent).mean(), s.iloc[-(recent + base):-recent].mean()
    return None if before == 0 else (now - before) / before * 100


def live_signals() -> dict:
    """Collect all live signals and flag the ones that look abnormal."""
    alerts = nws_alerts()
    wti, gas = daily_price("wti"), daily_price("gas")
    refin = eia_weekly()
    pa = portwatch_daily("Daily_Ports_Data", "Port Arthur", n=400)
    hou = portwatch_daily("Daily_Ports_Data", "Houston", n=400)
    pan = portwatch_daily("Daily_Chokepoints_Data", "Panama", n=400)

    def port_signal(df):
        col = tanker_column(df) if not df.empty else None
        return pct_change(df, col, recent=7, base=90) if col else None

    sig = {
        "weather":  {"value": len(alerts),
                     "flag": (not alerts.empty) and alerts["severity"].isin(["Severe", "Extreme"]).any(),
                     "detail": alerts},
        "wti":      {"value": pct_change(wti), "last": wti["value"].iloc[-1] if len(wti) else None},
        "gas":      {"value": pct_change(gas), "last": gas["value"].iloc[-1] if len(gas) else None},
        "refinery": {"value": refin["value"].iloc[-1] if len(refin) else None},
        "port_arthur": {"value": port_signal(pa)},
        "houston":     {"value": port_signal(hou)},
        "panama":      {"value": port_signal(pan)},
    }
    # Thresholds: simple, explainable rules (tune them in your backtest)
    sig["wti"]["flag"] = sig["wti"]["value"] is not None and abs(sig["wti"]["value"]) >= 10
    sig["gas"]["flag"] = sig["gas"]["value"] is not None and abs(sig["gas"]["value"]) >= 15
    sig["refinery"]["flag"] = sig["refinery"]["value"] is not None and sig["refinery"]["value"] < 85
    for k in ("port_arthur", "houston", "panama"):
        sig[k]["flag"] = sig[k]["value"] is not None and sig[k]["value"] <= -25
    # Last 12 months of each series, for the trend charts
    def last_year(df, col="value"):
        if df is None or df.empty or col not in df:
            return pd.DataFrame(columns=["date", "value"])
        out = df[["date", col]].rename(columns={col: "value"})
        return out[out["date"] >= out["date"].max() - pd.Timedelta(days=365)]

    def port_7d(df):
        col = tanker_column(df) if not df.empty else None
        if not col:
            return pd.DataFrame(columns=["date", "value"])
        d = df[["date", col]].copy()
        d["value"] = d[col].rolling(7, min_periods=7).mean()
        return last_year(d.dropna(subset=["value"]))

    sig["series"] = {
        "wti": last_year(wti), "gas": last_year(gas), "refinery": last_year(refin),
        "port_arthur": port_7d(pa), "panama": port_7d(pan),
    }
    sig["checked_at"] = dt.datetime.now(ZoneInfo("America/Chicago")).strftime("%b %d, %Y %I:%M %p") + " (Texas time)"
    return sig


def alert_level(structural_score: float, sig: dict) -> tuple:
    """Combine structural risk (0-1) with the number of live warning flags."""
    flags = sum(1 for k, v in sig.items() if isinstance(v, dict) and v.get("flag"))
    exposure = structural_score * (1 + 0.5 * flags)
    if sig["weather"]["flag"] or exposure >= 0.6:
        return "HIGH", flags
    if flags >= 1 or exposure >= 0.35:
        return "ELEVATED", flags
    return "NORMAL", flags
