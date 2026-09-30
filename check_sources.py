"""
Run this on your computer to test every live source:
    python check_sources.py
"""
import logging
logging.getLogger("streamlit").setLevel(logging.ERROR)   # hide cache warnings

import requests
from live_data import (CHOKEPOINTS, PORTS, LAST_ERRORS, daily_price, eia_weekly, nws_alerts,
                       portwatch_daily, tanker_column)

print("NWS alerts (Gulf Coast):", len(nws_alerts()), "active")
for name in ["wti", "brent", "gas"]:
    df = daily_price(name)
    print(f"Daily price {name}:", df.tail(1).to_dict("records") if len(df) else "FAILED")
df = eia_weekly()
print("EIA refinery utilization:", df.tail(1).to_dict("records") if len(df) else "no key or FAILED")
missing = False
for svc, places in [("Daily_Ports_Data", PORTS), ("Daily_Chokepoints_Data", CHOKEPOINTS)]:
    for k, v in places.items():
        df = portwatch_daily(svc, v["like"])
        if df.empty:
            missing = True
            print(f"PortWatch {v['label']}: FAILED or name not found")
        else:
            print(f"PortWatch {v['label']}: OK, matched {sorted(df['portname'].unique())}, "
                  f"latest {df['date'].max().date()}, tanker column: {tanker_column(df)}")
if missing:
    url = ("https://services9.arcgis.com/weJ1QsnbMYJlCHdG/ArcGIS/rest/services/"
           "Daily_Chokepoints_Data/FeatureServer/0/query")
    r = requests.get(url, params={"where": "1=1", "outFields": "portname",
                                  "returnDistinctValues": "true", "f": "json"}, timeout=30)
    print("\nAll PortWatch chokepoint names:",
          sorted({f["attributes"]["portname"] for f in r.json().get("features", [])}))
from freight import ERRORS as FR_ERRORS, freight_signals
fr = freight_signals()
for m, v in fr["modes"].items():
    print(f"BLS freight {m}:", f"OK, {v['value']} ({v['yoy']:+.1f}% yoy, {v['date']:%b %Y})" if v["yoy"] is not None else "FAILED")
for code, v in fr["market"].items():
    print(f"OilPriceAPI {code}:", v)
LAST_ERRORS.update(FR_ERRORS)
if LAST_ERRORS:
    print("\nErrors:")
    for k, v in LAST_ERRORS.items():
        print(" ", k, "->", v)
