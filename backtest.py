"""
Step 7: backtest the live alert rules on real past disruptions (2019-2024).

Run from the project folder:
    python backtest.py

What it does
  1. Downloads daily history: EIA WTI + Henry Hub prices, EIA weekly Gulf Coast
     refinery utilization, IMF PortWatch tanker calls (Port Arthur, Houston,
     Panama Canal).
  2. Recomputes every live signal for every past day, using the same rules as
     the dashboard.
  3. Tests three threshold sets (strict / base / loose) against known events:
     did an alert fire near the event, how many days before or after, and how
     often did it fire on quiet days (false alarms)?

Output: data/clean/backtest_daily.csv, backtest_events.csv, backtest_summary.csv

Limit to report honestly: the NWS API does not keep old weather alerts, so the
backtest uses only the price, refinery and port signals. In the live app the
weather alert is an extra, real-time layer on top.
"""

import os
import sys
import tomllib

import pandas as pd
import requests

START = "2019-01-01"
OUT = "data/clean"

# Known disruptions (start date = landfall / start of the event)
EVENTS = [
    ("Hurricane Laura (landfall near Port Arthur area)", "2020-08-27"),
    ("Winter Storm Uri (Texas freeze)", "2021-02-14"),
    ("Hurricane Ida (Louisiana)", "2021-08-29"),
    ("Panama Canal drought restrictions", "2023-08-01"),
    ("Hurricane Beryl (Houston area)", "2024-07-08"),
    ("Hurricane Francine (Louisiana)", "2024-09-11"),
]

# Alternative threshold sets (the "multiple alternatives" in testing)
RULESETS = {
    "strict": {"wti": 15, "gas": 25, "port": -40, "refinery": 80},
    "base":   {"wti": 10, "gas": 15, "port": -25, "refinery": 85},   # used in the app
    "loose":  {"wti": 5,  "gas": 10, "port": -15, "refinery": 88},
}

WINDOW_BEFORE, WINDOW_AFTER = 14, 14   # days around an event that count as "caught"
QUIET_GAP = 30                         # days away from any event = "quiet" day


# ------------------------------------------------------------------ download
def eia_key():
    try:
        with open(".streamlit/secrets.toml", "rb") as f:
            return tomllib.load(f)["EIA_KEY"]
    except Exception:
        sys.exit("EIA_KEY not found in .streamlit/secrets.toml")


def eia(series_id, key):
    r = requests.get(f"https://api.eia.gov/v2/seriesid/{series_id}",
                     params={"api_key": key, "start": START}, timeout=60)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["response"]["data"])[["period", "value"]]
    df.columns = ["date", "value"]
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df = df.dropna().sort_values("date")
    return df[df["date"] >= START].set_index("date")["value"]


def portwatch(service, name_like, col):
    url = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
           f"{service}/FeatureServer/0/query")
    rows, offset = [], 0
    while True:
        r = requests.get(url, params={"where": f"portname LIKE '%{name_like}%'",
                                      "outFields": f"date,{col}", "orderByFields": "date ASC",
                                      "resultOffset": offset, "resultRecordCount": 1000,
                                      "f": "json"}, timeout=60)
        r.raise_for_status()
        batch = [f["attributes"] for f in r.json().get("features", [])]
        rows += batch
        if len(batch) < 1000:
            break
        offset += 1000
    df = pd.DataFrame(rows)
    if pd.api.types.is_numeric_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], unit="ms")
    else:
        df["date"] = pd.to_datetime(df["date"])
    df["date"] = df["date"].dt.normalize()
    return df.groupby("date")[col].sum().sort_index()


# ------------------------------------------------------------------ signals
def pct_vs_baseline(s, recent, base):
    """Recent average vs the average of the `base` days before it, in percent."""
    now = s.rolling(recent, min_periods=recent).mean()
    before = s.shift(recent).rolling(base, min_periods=int(base * 0.8)).mean()
    return (now - before) / before * 100


def build_daily():
    key = eia_key()
    print("Downloading EIA prices and refinery data ...")
    wti = eia("PET.RWTC.D", key)
    gas = eia("NG.RNGWHHD.D", key)
    ref = eia("PET.W_NA_YUP_R30_PER.W", key)
    print("Downloading PortWatch history (this can take a minute) ...")
    pa = portwatch("Daily_Ports_Data", "Port Arthur", "portcalls_tanker")
    hou = portwatch("Daily_Ports_Data", "Houston", "portcalls_tanker")
    pan = portwatch("Daily_Chokepoints_Data", "Panama", "n_tanker")

    days = pd.date_range(START, max(s.index.max() for s in [wti, gas, pa, hou, pan]), freq="D")
    d = pd.DataFrame(index=days)
    # Prices trade on business days: 5 trading days vs 60 trading days, then carry to calendar days
    d["wti_chg"] = pct_vs_baseline(wti, 5, 60).reindex(days).ffill(limit=4)
    d["gas_chg"] = pct_vs_baseline(gas, 5, 60).reindex(days).ffill(limit=4)
    d["refinery"] = ref.reindex(days).ffill(limit=7)
    for name, s in [("port_arthur", pa), ("houston", hou), ("panama", pan)]:
        full = pd.date_range(s.index.min(), s.index.max(), freq="D")
        s = s.reindex(full).fillna(0)                    # no ships that day = 0 calls
        d[f"{name}_chg"] = pct_vs_baseline(s, 7, 90).reindex(days)
    d.index.name = "date"
    print("Coverage:", {c: str(d[c].first_valid_index().date()) for c in d.columns
                        if d[c].first_valid_index() is not None})
    return d


def flags(d, rules):
    f = pd.DataFrame(index=d.index)
    f["wti"] = d["wti_chg"].abs() >= rules["wti"]
    f["gas"] = d["gas_chg"].abs() >= rules["gas"]
    f["refinery"] = d["refinery"] < rules["refinery"]
    for p in ["port_arthur", "houston", "panama"]:
        f[p] = d[f"{p}_chg"] <= rules["port"]
    return f


# ------------------------------------------------------------------ evaluate
def evaluate(d):
    event_rows, summary = [], []
    near_event = pd.Series(False, index=d.index)
    for _, start in EVENTS:
        t = pd.Timestamp(start)
        near_event |= (d.index >= t - pd.Timedelta(days=QUIET_GAP)) & \
                      (d.index <= t + pd.Timedelta(days=QUIET_GAP))
    quiet = ~near_event

    for rs_name, rules in RULESETS.items():
        f = flags(d, rules)
        n_flags = f.sum(axis=1)
        for level, need in [("ELEVATED (1+ flags)", 1), ("HIGH (2+ flags)", 2)]:
            alert = n_flags >= need
            caught, leads = 0, []
            for ev, start in EVENTS:
                t = pd.Timestamp(start)
                win = alert[(alert.index >= t - pd.Timedelta(days=WINDOW_BEFORE)) &
                            (alert.index <= t + pd.Timedelta(days=WINDOW_AFTER))]
                hit = win[win]
                first = hit.index.min() if len(hit) else None
                lead = (first - t).days if first is not None else None
                if first is not None:
                    caught += 1
                    leads.append(lead)
                which = f.loc[hit.index].any() if len(hit) else pd.Series(dtype=bool)
                event_rows.append({
                    "ruleset": rs_name, "level": level, "event": ev, "event_date": start,
                    "caught": first is not None,
                    "first_alert": first.date() if first is not None else "",
                    "days_vs_event": lead if lead is not None else "",
                    "signals_that_fired": ", ".join(which[which].index) if len(which) else "",
                })
            summary.append({
                "ruleset": rs_name, "level": level,
                "events_caught": f"{caught} of {len(EVENTS)}",
                "median_days_vs_event": pd.Series(leads).median() if leads else None,
                "false_alarm_rate_%": round(alert[quiet].mean() * 100, 1),
            })
    return pd.DataFrame(event_rows), pd.DataFrame(summary)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    daily = build_daily()
    daily.to_csv(f"{OUT}/backtest_daily.csv")
    events, summary = evaluate(daily)
    events.to_csv(f"{OUT}/backtest_events.csv", index=False)
    summary.to_csv(f"{OUT}/backtest_summary.csv", index=False)
    pd.set_option("display.width", 160)
    print("\nSUMMARY (days_vs_event: negative = alert came BEFORE the event)")
    print(summary.to_string(index=False))
    print("\nBASE rules, per event:")
    print(events[events["ruleset"] == "base"].to_string(index=False))
    print(f"\nSaved to {OUT}/backtest_*.csv")
