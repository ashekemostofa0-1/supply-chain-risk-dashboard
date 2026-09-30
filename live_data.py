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
                                 "effective": p.get("effective") or p.get("onset"),
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
        params = {"where": f"portname LIKE '%{name_like}%'",
                  "outFields": "date,portname,portcalls_tanker,n_tanker,portcalls,n_total",
                  "orderByFields": "date DESC", "resultRecordCount": n, "f": "json"}
        r = None
        for attempt in range(3):                  # the server is sometimes slow: retry twice
            try:
                r = requests.get(f"{PORTWATCH}/{service}/FeatureServer/0/query", params=params, timeout=45)
                if r.ok and "error" in r.json():  # unknown field for this layer -> ask for all fields
                    params["outFields"] = "*"
                    continue
                break
            except requests.exceptions.Timeout:
                if attempt == 2:
                    raise
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
    """Daily spot price: EIA first (needs key), FRED as backup.
    wti = WTI crude, brent = Brent crude ($/bbl); gas = Henry Hub ($/MMBtu)."""
    eia_id, fred_id = {"wti": ("PET.RWTC.D", "DCOILWTICO"),
                       "brent": ("PET.RBRTE.D", "DCOILBRENTEU"),
                       "gas": ("NG.RNGWHHD.D", "DHHNGSP")}[name]
    df = eia_series(eia_id)
    return df if len(df) else fred_daily(fred_id)


# ---------------------------------------------------------------- GLOBAL DISASTERS (GDACS)
GDACS_TYPES = {"TC": "Tropical cyclone", "EQ": "Earthquake", "FL": "Flood", "VO": "Volcano",
               "WF": "Wildfire", "DR": "Drought"}


@st.cache_data(ttl=1800, show_spinner=False)          # refresh every 30 minutes
def _gdacs(event_type: str, from_date: str, to_date: str) -> list:
    r = requests.get("https://www.gdacs.org/gdacsapi/api/events/geteventlist/SEARCH",
                     params={"eventlist": event_type, "fromDate": from_date, "toDate": to_date,
                             "alertlevel": "Green;Orange;Red", "pageSize": 100},
                     headers=HEADERS, timeout=25)
    r.raise_for_status()
    out = []
    for f in r.json().get("features", []):
        p, g = f.get("properties", {}), f.get("geometry") or {}
        if g.get("type") != "Point":
            continue
        if str(p.get("iscurrent", "true")).lower() == "false":
            continue
        lon, lat = g["coordinates"][:2]
        sev = p.get("severitydata") or {}
        out.append({"type": event_type, "kind": GDACS_TYPES[event_type],
                    "name": p.get("eventname") or p.get("name") or "",
                    "alert": (p.get("alertlevel") or "Green").title(),
                    "country": p.get("country") or "", "lat": float(lat), "lon": float(lon),
                    "severity": sev.get("severitytext", "") if isinstance(sev, dict) else "",
                    "from": str(p.get("fromdate", ""))[:10], "to": str(p.get("todate", ""))[:10]})
    return out


def gdacs_events(days: int = 14) -> list:
    """Current worldwide disasters from GDACS (UN / European Commission). Empty list on failure."""
    today = dt.date.today()
    frm, to = (today - dt.timedelta(days=days)).isoformat(), (today + dt.timedelta(days=1)).isoformat()
    events = []
    for t in GDACS_TYPES:
        try:
            events += _gdacs(t, frm, to)
        except Exception as e:
            LAST_ERRORS[f"GDACS {t}"] = repr(e)[:200]
    # keep one entry per event name and type (latest episode)
    seen, uniq = set(), []
    for e in sorted(events, key=lambda e: e["to"], reverse=True):
        key = (e["type"], e["name"], round(e["lat"]), round(e["lon"]))
        if key not in seen:
            seen.add(key)
            uniq.append(e)
    return uniq


# Chokepoints on the main oil routes (IMF PortWatch names are matched with LIKE)
CHOKEPOINTS = {
    "panama":    {"label": "Panama Canal",       "like": "Panama",    "lat": 9.1,   "lng": -79.7},
    "suez":      {"label": "Suez Canal",         "like": "Suez",      "lat": 30.6,  "lng": 32.3},
    "bab":       {"label": "Bab el-Mandeb",      "like": "Mandeb",    "lat": 12.6,  "lng": 43.4},
    "hormuz":    {"label": "Strait of Hormuz",   "like": "Hormuz",    "lat": 26.6,  "lng": 56.3},
    "good_hope": {"label": "Cape of Good Hope",  "like": "Good Hope", "lat": -34.4, "lng": 18.5},
    "malacca":   {"label": "Malacca Strait",     "like": "Malacca",   "lat": 2.5,   "lng": 101.3},
}
PORTS = {
    "port_arthur": {"label": "Port Arthur", "like": "Port Arthur", "lat": 29.87, "lng": -93.93},
    "houston":     {"label": "Houston",     "like": "Houston",     "lat": 29.73, "lng": -95.0},
}

# Weather events that can actually stop refineries, plants, ports or rail
SUPPLY_WEATHER = ["hurricane", "tropical storm", "storm surge", "flood", "freeze",
                  "winter storm", "ice storm", "extreme cold", "blizzard", "tornado"]


# ---------------------------------------------------------------- SIGNALS
def pct_change(df: pd.DataFrame, col: str = "value", recent: int = 5, base: int = 60):
    """Recent average vs. baseline average, in percent. None if not enough data."""
    if df is None or df.empty or col not in df or len(df) < recent + base:
        return None
    s = df[col].astype(float)
    now, before = s.tail(recent).mean(), s.iloc[-(recent + base):-recent].mean()
    return None if before == 0 else (now - before) / before * 100


def _last_date(df):
    return None if df is None or df.empty else pd.Timestamp(df["date"].max())


def live_signals() -> dict:
    """Collect all live signals and flag the ones that look abnormal."""
    alerts = nws_alerts()
    wti, brent, gas = daily_price("wti"), daily_price("brent"), daily_price("gas")
    refin = eia_weekly()
    port_df = {k: portwatch_daily("Daily_Ports_Data", v["like"], n=400) for k, v in PORTS.items()}
    choke_df = {k: portwatch_daily("Daily_Chokepoints_Data", v["like"], n=400)
                for k, v in CHOKEPOINTS.items()}

    def traffic_signal(df):
        col = tanker_column(df) if not df.empty else None
        return pct_change(df, col, recent=7, base=90) if col else None

    # Weather: only supply-relevant events that the NWS rates Severe or Extreme
    if not alerts.empty:
        alerts = alerts.copy()
        alerts["supply_relevant"] = [any(w in str(e).lower() for w in SUPPLY_WEATHER)
                                     for e in alerts["event"].tolist()]
        alerts["supply_relevant"] = alerts["supply_relevant"].astype(bool)
        is_sev = pd.Series([str(v) in ("Severe", "Extreme") for v in alerts["severity"].tolist()],
                           index=alerts.index, dtype=bool)
        severe = alerts[alerts["supply_relevant"] & is_sev]
    else:
        severe = alerts
    sig = {
        "weather": {"value": len(alerts), "relevant": len(severe), "flag": len(severe) > 0,
                    "detail": alerts, "events": sorted(set(severe["event"])) if len(severe) else []},
        "wti":   {"value": pct_change(wti),   "last": wti["value"].iloc[-1] if len(wti) else None,
                  "date": _last_date(wti)},
        "brent": {"value": pct_change(brent), "last": brent["value"].iloc[-1] if len(brent) else None,
                  "date": _last_date(brent)},
        "gas":   {"value": pct_change(gas),   "last": gas["value"].iloc[-1] if len(gas) else None,
                  "date": _last_date(gas)},
        "refinery": {"value": refin["value"].iloc[-1] if len(refin) else None, "date": _last_date(refin)},
    }
    for k, df in {**port_df, **choke_df}.items():
        sig[k] = {"value": traffic_signal(df), "date": _last_date(df)}

    # Thresholds: simple, explainable rules (the same ones backtest.py tests)
    sig["wti"]["flag"] = sig["wti"]["value"] is not None and abs(sig["wti"]["value"]) >= 10
    sig["gas"]["flag"] = sig["gas"]["value"] is not None and abs(sig["gas"]["value"]) >= 15
    sig["brent"]["flag"] = False            # shown for context; WTI carries the oil-price flag
    sig["refinery"]["flag"] = sig["refinery"]["value"] is not None and sig["refinery"]["value"] < 85
    for k in list(PORTS) + list(CHOKEPOINTS):
        sig[k]["flag"] = sig[k]["value"] is not None and sig[k]["value"] <= -25

    # Last 12 months of each series, for the trend charts
    def last_year(df, col="value"):
        if df is None or df.empty or col not in df:
            return pd.DataFrame(columns=["date", "value"])
        out = df[["date", col]].rename(columns={col: "value"})
        return out[out["date"] >= out["date"].max() - pd.Timedelta(days=365)]

    def traffic_7d(df):
        col = tanker_column(df) if not df.empty else None
        if not col:
            return pd.DataFrame(columns=["date", "value"])
        d = df[["date", col]].copy()
        d["value"] = d[col].rolling(7, min_periods=7).mean()
        return last_year(d.dropna(subset=["value"]))

    sig["series"] = {"wti": last_year(wti), "brent": last_year(brent), "gas": last_year(gas),
                     "refinery": last_year(refin)}
    sig["series"].update({k: traffic_7d(df) for k, df in {**port_df, **choke_df}.items()})
    # Longer price history for the procurement simulator's volatility estimate
    sig["prices_full"] = {"wti": wti, "brent": brent, "gas": gas}
    # raw daily tanker counts (used to compare today's signals with earlier days)
    sig["traffic_raw"] = {}
    for k, d_ in {**port_df, **choke_df}.items():
        col = tanker_column(d_) if not d_.empty else None
        if col:
            sig["traffic_raw"][k] = d_[["date", col]].rename(columns={col: "value"})
    sig["disasters"] = gdacs_events()
    from freight import freight_signals          # free BLS freight indexes + OilPriceAPI market indexes
    sig["freight"] = freight_signals()
    sig["checked_at"] = dt.datetime.now(ZoneInfo("America/Chicago")).strftime("%b %d, %Y %I:%M %p") + " (Texas time)"
    return sig


# Signals that count toward an industry's alert level (chokepoints feed the route table)
INDUSTRY_SIGNALS = ["weather", "wti", "gas", "refinery", "port_arthur", "houston", "panama"]
FRAGILE = 0.35     # structural score at or above this = fragile industry


def alert_level(structural_score: float, sig: dict) -> tuple:
    """Live pressure sets the level; the structural score decides whether it reaches HIGH.

    pressure = number of live warning flags (a supply-relevant severe weather alert counts 2)
      0      -> NORMAL
      1      -> ELEVATED
      2 or +  -> HIGH for fragile industries (score >= 0.35), ELEVATED for sturdier ones
    """
    flags = [k for k in INDUSTRY_SIGNALS if sig.get(k, {}).get("flag")]
    pressure = len(flags) + (1 if "weather" in flags else 0)
    if pressure == 0:
        level = "NORMAL"
    elif pressure == 1:
        level = "ELEVATED"
    else:
        level = "HIGH" if structural_score >= FRAGILE else "ELEVATED"
    return level, len(flags)
