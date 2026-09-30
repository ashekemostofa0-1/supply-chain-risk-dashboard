"""
Route risk: which main oil and chemical sea lanes are under pressure right now.

Each route lists the live signals that sit on it (Gulf Coast weather, Gulf ports,
chokepoints). Risk = how many of those signals are flagged:
    0 flagged -> Normal, 1 -> Elevated, 2 or more -> High.
"""

import pandas as pd
import plotly.graph_objects as go

from live_data import CHOKEPOINTS, PORTS
from ui_style import STATUS

GULF = ["weather", "port_arthur", "houston"]
SIGNAL_NAMES = {"weather": "Gulf Coast weather", "port_arthur": "Port Arthur", "houston": "Houston",
                **{k: v["label"] for k, v in CHOKEPOINTS.items()}}

# Typical tanker voyage times are approximate (about 12-13 knots, no port delays)
ROUTES = [
    {"name": "US Gulf → Northwest Europe", "signals": GULF, "typical": "15–18 days",
     "points": [[29.87, -93.93], [27.5, -90.0], [24.6, -83.5], [24.3, -81.0], [26.5, -79.3],
                [32.0, -75.0], [38.0, -60.0], [43.0, -40.0], [47.0, -20.0], [49.5, -6.0],
                [51.0, 1.5], [51.95, 4.10]]},
    {"name": "US Gulf → Northeast Asia (via Panama)", "signals": GULF + ["panama"], "typical": "28–33 days",
     "points": [[29.73, -95.00], [27.0, -93.0], [22.0, -88.0], [21.5, -86.3], [17.0, -82.0],
                [12.0, -80.5], [9.35, -79.90], [8.90, -79.50], [7.0, -82.0], [12.0, -100.0],
                [20.0, -130.0], [28.0, -160.0], [33.0, 170.0], [34.2, 145.0], [35.30, 139.80]]},
    {"name": "US Gulf → South America (Brazil)", "signals": GULF, "typical": "16–19 days",
     "points": [[27.80, -97.40], [25.0, -94.0], [22.0, -88.0], [21.3, -86.0], [18.0, -76.0],
                [13.0, -62.0], [5.0, -45.0], [-2.0, -36.0], [-10.0, -34.0], [-20.0, -39.0],
                [-23.95, -46.30]]},
    {"name": "Middle East → US Gulf (via Suez)", "signals": ["hormuz", "bab", "suez"] + GULF,
     "typical": "30–35 days",
     "points": [[26.64, 50.16], [26.5, 56.5], [22.0, 62.0], [13.0, 51.0], [12.6, 43.4],
                [20.0, 38.5], [27.5, 34.0], [30.0, 32.5], [33.5, 28.0], [36.5, 15.0],
                [36.0, -5.6], [35.0, -20.0], [30.0, -45.0], [26.0, -70.0], [24.3, -81.0],
                [24.8, -84.5], [27.5, -90.0], [29.87, -93.93]]},
    {"name": "Middle East → US Gulf (via Cape of Good Hope)", "signals": ["hormuz", "good_hope"] + GULF,
     "typical": "40–45 days",
     "points": [[26.64, 50.16], [26.5, 56.5], [20.0, 62.0], [5.0, 58.0], [-10.0, 50.0],
                [-25.0, 40.0], [-34.8, 20.0], [-30.0, 8.0], [-15.0, -8.0], [3.0, -25.0],
                [15.0, -50.0], [22.0, -70.0], [24.3, -81.0], [24.8, -84.5], [27.5, -90.0],
                [29.87, -93.93]]},
]


def signal_level(sig: dict, key: str) -> str:
    """Status of one signal: flagged = HIGH, weakening = MONITOR, else NORMAL."""
    s = sig.get(key, {})
    if key == "weather":
        return "HIGH" if s.get("flag") else "NORMAL"
    v = s.get("value")
    if v is None:
        return "NODATA"
    if s.get("flag"):
        return "HIGH"
    return "MONITOR" if v <= -10 else "NORMAL"


def route_table(sig: dict) -> pd.DataFrame:
    rows = []
    for r in ROUTES:
        flagged = [k for k in r["signals"] if sig.get(k, {}).get("flag")]
        measured = [k for k in r["signals"] if k == "weather" or sig.get(k, {}).get("value") is not None]
        if not measured:
            level = "NODATA"
        else:
            level = "HIGH" if len(flagged) >= 2 else "ELEVATED" if len(flagged) == 1 else "NORMAL"
        traffic = [(k, sig[k]["value"]) for k in r["signals"]
                   if k != "weather" and sig.get(k, {}).get("value") is not None]
        worst = min(traffic, key=lambda t: t[1]) if traffic else None
        rows.append({
            "Route": r["name"],
            "Risk": level,
            "Typical voyage (approx.)": r["typical"],
            "Weakest point, tanker traffic 7d vs 90d":
                f"{SIGNAL_NAMES[worst[0]]} {worst[1]:+.0f}%" if worst else "no data",
            "Warning signals": ", ".join(SIGNAL_NAMES[k] for k in flagged) or "none",
        })
    return pd.DataFrame(rows)


def route_map(sig: dict, table: pd.DataFrame) -> go.Figure:
    fig = go.Figure()
    level_of = dict(zip(table["Route"], table["Risk"]))
    for r in ROUTES:
        lvl = level_of[r["name"]]
        lat, lon = zip(*r["points"])
        fig.add_trace(go.Scattergeo(
            lat=lat, lon=lon, mode="lines", line=dict(width=3, color=STATUS[lvl]["fg"]),
            opacity=0.85, showlegend=False, hoverinfo="text",
            text=f"<b>{r['name']}</b><br>Risk: {STATUS[lvl]['label']}<br>Typical voyage: {r['typical']}"))
    # Chokepoints and Gulf ports, colored by their own status
    points = [(k, v, "chokepoint") for k, v in CHOKEPOINTS.items()] + \
             [(k, v, "port") for k, v in PORTS.items()]
    for k, v, kind in points:
        lvl = signal_level(sig, k)
        val = sig.get(k, {}).get("value")
        detail = f"tanker traffic {val:+.0f}% (7d vs 90d)" if val is not None else "no data"
        fig.add_trace(go.Scattergeo(
            lat=[v["lat"]], lon=[v["lng"]], mode="markers+text",
            marker=dict(size=13 if kind == "chokepoint" else 10, color=STATUS[lvl]["fg"],
                        line=dict(width=2, color="#FFFFFF"),
                        symbol="diamond" if kind == "chokepoint" else "circle"),
            text=[v["label"]], textposition="top center",
            textfont=dict(size=11, color="#0F172A"), showlegend=False, hoverinfo="text",
            hovertext=f"<b>{v['label']}</b><br>{STATUS[lvl]['label']}: {detail}"))
    # Legend entries for the status colors
    for lvl in ["HIGH", "ELEVATED", "MONITOR", "NORMAL"]:
        fig.add_trace(go.Scattergeo(lat=[None], lon=[None], mode="markers",
                                    marker=dict(size=10, color=STATUS[lvl]["fg"]),
                                    name=STATUS[lvl]["label"], showlegend=True))
    fig.update_geos(
        projection_type="natural earth", projection_rotation=dict(lon=-30),
        showland=True, landcolor="#E7ECF3", showocean=True, oceancolor="#F7FAFF",
        showcountries=True, countrycolor="#CBD5E1", showcoastlines=False,
        showframe=False, lataxis_range=[-50, 72])
    fig.update_layout(height=430, margin=dict(l=0, r=0, t=0, b=0),
                      paper_bgcolor="rgba(0,0,0,0)",
                      legend=dict(orientation="h", y=1.02, x=0, bgcolor="rgba(255,255,255,0.8)"))
    return fig
