"""
Run this on your computer to test every live source:
    python check_sources.py
"""
import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)   # hide cache warnings

from live_data import (nws_alerts, daily_price, eia_weekly, portwatch_daily,
                       tanker_column, LAST_ERRORS)

print("NWS alerts (Gulf Coast):", len(nws_alerts()), "active")
for name in ["wti", "gas"]:
    df = daily_price(name)
    print(f"Daily price {name}:", df.tail(1).to_dict("records") if len(df) else "FAILED")
df = eia_weekly()
print("EIA refinery utilization:", df.tail(1).to_dict("records") if len(df) else "no key or FAILED")
for svc, name in [("Daily_Ports_Data", "Port Arthur"), ("Daily_Ports_Data", "Houston"),
                  ("Daily_Chokepoints_Data", "Panama")]:
    df = portwatch_daily(svc, name)
    if df.empty:
        print(f"PortWatch {name}: FAILED")
    else:
        print(f"PortWatch {name}: OK, {len(df)} days, latest {df['date'].max().date()}, "
              f"tanker column: {tanker_column(df)}")
if LAST_ERRORS:
    print("\nErrors:")
    for k, v in LAST_ERRORS.items():
        print(" ", k, "->", v)
