"""
Route risk: which main oil and chemical sea lanes are under pressure right now.

Each route lists the live signals that sit on it (Gulf Coast weather, Gulf ports,
chokepoints). Risk = how many of those signals are flagged:
    0 flagged -> Low, 1 -> Medium, 2 or more -> High.
Trend = direction of tanker traffic at the route's weakest point (falling traffic = rising risk).
"""

import html

import pandas as pd
import plotly.graph_objects as go

from live_data import CHOKEPOINTS, PORTS
from ui_style import STATUS, pill

GULF = ["weather", "port_arthur", "houston"]
SIGNAL_NAMES = {"weather": "Gulf Coast weather", "port_arthur": "Port Arthur", "houston": "Houston",
                **{k: v["label"] for k, v in CHOKEPOINTS.items()}}

_ME = [[26.64, 50.16], [26.5, 56.5], [22.0, 62.0]]
_SUEZ = [[13.0, 51.0], [12.6, 43.4], [20.0, 38.5], [27.5, 34.0], [30.0, 32.5], [33.5, 28.0]]
# Typical tanker voyage times are approximate (about 12-13 knots, no port delays)
ROUTES = [
    {"name": "Middle East → Northeast Asia", "origin": "Middle East", "dest": "Northeast Asia",
     "signals": ["hormuz", "malacca"], "typical": "20–24 days",
     "points": _ME + [[12.0, 72.0], [6.0, 80.0], [5.8, 95.0], [2.5, 101.5], [1.3, 104.0],
                      [10.0, 112.0], [22.0, 120.0], [30.0, 128.0], [35.3, 139.8]]},
    {"name": "US Gulf → Europe", "origin": "US Gulf Coast", "dest": "Europe", "signals": GULF,
     "typical": "15–18 days",
     "points": [[29.87, -93.93], [27.5, -90.0], [24.6, -83.5], [24.3, -81.0], [26.5, -79.3],
                [32.0, -75.0], [38.0, -60.0], [43.0, -40.0], [47.0, -20.0], [49.5, -6.0],
                [51.0, 1.5], [51.95, 4.10]]},
    {"name": "US Gulf → Northeast Asia (via Panama)", "origin": "US Gulf Coast", "dest": "Northeast Asia",
     "signals": GULF + ["panama"], "typical": "28–33 days",
     "points": [[29.73, -95.00], [27.0, -93.0], [22.0, -88.0], [21.5, -86.3], [17.0, -82.0],
                [12.0, -80.5], [9.35, -79.90], [8.90, -79.50], [7.0, -82.0], [12.0, -100.0],
                [20.0, -130.0], [28.0, -160.0], [33.0, 170.0], [34.2, 145.0], [35.30, 139.80]]},
    {"name": "US Gulf → South America", "origin": "US Gulf Coast", "dest": "South America",
     "signals": GULF, "typical": "16–19 days",
     "points": [[27.80, -97.40], [25.0, -94.0], [22.0, -88.0], [21.3, -86.0], [18.0, -76.0],
                [13.0, -62.0], [5.0, -45.0], [-2.0, -36.0], [-10.0, -34.0], [-20.0, -39.0],
                [-23.95, -46.30]]},
    {"name": "Middle East → Europe (via Suez)", "origin": "Middle East", "dest": "Europe",
     "signals": ["hormuz", "bab", "suez"], "typical": "20–24 days",
     "points": _ME + _SUEZ + [[36.5, 15.0], [36.0, -5.6], [43.0, -10.0], [48.5, -5.5], [51.95, 4.1]]},
    {"name": "Middle East → Europe (via Cape of Good Hope)", "origin": "Middle East", "dest": "Europe",
     "signals": ["hormuz", "good_hope"], "typical": "32–36 days",
     "points": _ME + [[5.0, 58.0], [-10.0, 50.0], [-25.0, 40.0], [-34.8, 20.0], [-30.0, 8.0], [-15.0, -2.0],
                      [0.0, -10.0], [15.0, -20.0], [30.0, -15.0], [43.0, -10.0], [48.5, -5.5], [51.95, 4.1]]},
    {"name": "Middle East → US Gulf (via Suez)", "origin": "Middle East", "dest": "US Gulf Coast",
     "signals": ["hormuz", "bab", "suez"] + GULF, "typical": "30–35 days",
     "points": _ME + _SUEZ + [[36.5, 15.0], [36.0, -5.6], [35.0, -20.0], [30.0, -45.0], [26.0, -70.0],
                              [24.3, -81.0], [24.8, -84.5], [27.5, -90.0], [29.87, -93.93]]},
    {"name": "Middle East → US Gulf (via Cape of Good Hope)", "origin": "Middle East", "dest": "US Gulf Coast",
     "signals": ["hormuz", "good_hope"] + GULF, "typical": "40–45 days",
     "points": _ME + [[5.0, 58.0], [-10.0, 50.0], [-25.0, 40.0], [-34.8, 20.0], [-30.0, 8.0],
                      [-15.0, -8.0], [3.0, -25.0], [15.0, -50.0], [22.0, -70.0], [24.3, -81.0],
                      [24.8, -84.5], [27.5, -90.0], [29.87, -93.93]]},
]


def is_exact(origin: str, dest: str) -> bool:
    return any(((r["origin"], r["dest"]) in ((origin, dest), (dest, origin))) for r in ROUTES) \
        or "All Regions" in (origin, dest)


def filter_routes(origin: str, dest: str):
    """Exact origin+destination match first; otherwise routes touching either region; else all."""
    def match(r, o, d):
        return (o == "All Regions" or r["origin"] == o) and (d == "All Regions" or r["dest"] == d)
    exact = [r for r in ROUTES if match(r, origin, dest) or match(r, dest, origin)]   # either direction
    if exact:
        return exact
    either = [r for r in ROUTES if r["origin"] in (origin, dest) or r["dest"] in (origin, dest)]
    return either or ROUTES


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


def route_table(sig: dict, routes=None) -> pd.DataFrame:
    rows = []
    for r in routes if routes is not None else ROUTES:
        flagged = [k for k in r["signals"] if sig.get(k, {}).get("flag")]
        measured = [k for k in r["signals"] if k == "weather" or sig.get(k, {}).get("value") is not None]
        level = "NODATA" if not measured else \
            "HIGH" if len(flagged) >= 2 else "ELEVATED" if len(flagged) == 1 else "NORMAL"
        traffic = [(k, sig[k]["value"]) for k in r["signals"]
                   if k != "weather" and sig.get(k, {}).get("value") is not None]
        worst = min(traffic, key=lambda t: t[1]) if traffic else None
        trend = "flat" if worst is None or abs(worst[1]) < 10 else ("up" if worst[1] < 0 else "down")
        rows.append({"route": r["name"], "level": level, "typical": r["typical"], "trend": trend,
                     "worst": f"{SIGNAL_NAMES[worst[0]]} tankers {worst[1]:+.0f}%" if worst else "no traffic data",
                     "flags": ", ".join(SIGNAL_NAMES[k] for k in flagged) or "none"})
    return pd.DataFrame(rows)


_ARROW = {"up": ("↗", "#DC2626", "Risk rising"), "down": ("↘", "#16A34A", "Risk easing"),
          "flat": ("→", "#EA580C", "Steady")}


def route_table_html(table: pd.DataFrame) -> str:
    if table.empty:
        return '<div class="csub">No routes match the selected origin and destination.</div>'
    body = "".join(
        f'<tr><td>{html.escape(r.route)}</td><td>{pill(r.level)}</td><td>{html.escape(r.typical)}</td>'
        f'<td title="{html.escape(_ARROW[r.trend][2])}: {html.escape(r.worst)}" '
        f'style="color:{_ARROW[r.trend][1]};font-size:18px;font-weight:700;text-align:center">'
        f'{_ARROW[r.trend][0]}</td></tr>'
        for r in table.itertuples())
    return (f'<div class="tbl-wrap"><table class="rt"><tr><th>Route</th><th>Risk Level</th>'
            f'<th>Est. Transit Time</th><th style="text-align:center">Trend</th></tr>{body}</table></div>')


# Bright, clearly different colors for the map (text elsewhere keeps the darker STATUS inks)
MAP_COLORS = {"HIGH": "#E11D2E", "ELEVATED": "#FFC400", "MONITOR": "#1E5BFF", "NORMAL": "#FFFFFF",
              "NODATA": "#CBD5E1"}
PORT_BLUE = "#0B2A6B"          # navy pins, so they differ from the blue Monitor color
OUTLINE = "#0B2545"            # dark edge under every line and marker, so white stays visible


def route_map(sig: dict, table: pd.DataFrame, routes) -> go.Figure:
    fig = go.Figure()
    level_of = dict(zip(table["route"], table["level"]))
    # draw calmer routes first so High routes sit on top
    order = {"NODATA": 0, "NORMAL": 1, "MONITOR": 2, "ELEVATED": 3, "HIGH": 4}
    for r in sorted(routes, key=lambda r: order[level_of.get(r["name"], "NODATA")]):
        lvl = level_of.get(r["name"], "NODATA")
        c = MAP_COLORS[lvl]
        lat, lon = zip(*r["points"])
        tip = f"<b>{r['name']}</b><br>Risk: {STATUS[lvl]['label']}<br>Typical voyage: {r['typical']}"
        fig.add_trace(go.Scattergeo(lat=lat, lon=lon, mode="lines", line=dict(width=6, color=OUTLINE),
                                    opacity=0.45, showlegend=False, hoverinfo="skip"))      # dark edge
        fig.add_trace(go.Scattergeo(lat=lat, lon=lon, mode="lines", line=dict(width=3.2, color=c),
                                    showlegend=False, hoverinfo="text", text=tip))
        # arrow-like end dot at the destination
        fig.add_trace(go.Scattergeo(lat=[lat[-1]], lon=[lon[-1]], mode="markers", showlegend=False,
                                    marker=dict(size=9, color=c, line=dict(width=2, color=OUTLINE)),
                                    hoverinfo="skip"))
    used = {k for r in routes for k in r["signals"]}
    places = [(k, v, "choke") for k, v in CHOKEPOINTS.items() if k in used] + \
             [(k, v, "port") for k, v in PORTS.items() if k in used]
    for k, v, kind in places:
        lvl = signal_level(sig, k)
        val = sig.get(k, {}).get("value")
        detail = f"tankers {val:+.0f}% vs 90-day avg" if val is not None else "no data"
        hover = f"<b>{v['label']}</b><br>{STATUS[lvl]['label']}: {detail}"
        if kind == "port":
            # blue anchor pin for ports, like a map app
            fig.add_trace(go.Scattergeo(lat=[v["lat"]], lon=[v["lng"]], mode="markers+text", showlegend=False,
                                        marker=dict(size=20, color=PORT_BLUE, line=dict(width=2, color="#fff")),
                                        text=["⚓"], textfont=dict(size=11, color="#fff"), textposition="middle center",
                                        hoverinfo="text", hovertext=hover))
            continue
        callout = lvl in ("HIGH", "ELEVATED", "MONITOR")
        c = MAP_COLORS[lvl]
        fig.add_trace(go.Scattergeo(
            lat=[v["lat"]], lon=[v["lng"]], mode="markers+text", showlegend=False,
            marker=dict(size=26 if callout else 12, color=c, line=dict(width=2.5, color=OUTLINE),
                        symbol="triangle-up" if lvl == "HIGH" else "circle"),
            text=["!" if callout else ""],
            textfont=dict(size=13, color="#0B2545" if lvl == "ELEVATED" else "#fff", family="Inter, Arial Black"),
            textposition="middle center", hoverinfo="text", hovertext=hover))
        if callout:
            word = {"HIGH": "Higher risk", "ELEVATED": "Elevated risk", "MONITOR": "Monitor"}[lvl]
            fig.add_trace(go.Scattergeo(
                lat=[v["lat"]], lon=[v["lng"]], mode="text", showlegend=False, hoverinfo="skip",
                text=[f"<b>{v['label']}</b><br>{word}<br><b>{val:+.0f}% tankers</b>" if val is not None
                      else f"<b>{v['label']}</b><br>{word}"],
                textposition="middle right" if v["lng"] < 60 else "middle left",
                textfont=dict(size=11.5, color="#0B2545", shadow="0 0 3px #fff, 0 0 3px #fff, 0 0 3px #fff")))
    fig.update_geos(
        projection_type="natural earth", projection_rotation=dict(lon=-10, lat=0),
        showocean=True, oceancolor="#8ED1FC",                       # sky-blue sea
        showland=True, landcolor="#F3EEDC",                         # light sand land
        showcountries=True, countrycolor="#C9BFA3", countrywidth=0.5,
        showcoastlines=True, coastlinecolor="#5FA8D3", coastlinewidth=0.8,
        showlakes=True, lakecolor="#8ED1FC", showrivers=False,
        showframe=False, lataxis_range=[-55, 75], bgcolor="rgba(0,0,0,0)")
    fig.update_layout(height=360, margin=dict(l=0, r=0, t=0, b=0), paper_bgcolor="rgba(0,0,0,0)",
                      hoverlabel=dict(bgcolor="#fff", font_size=12))
    return fig


def map_legend_html() -> str:
    items = [("HIGH", "High Risk"), ("ELEVATED", "Medium Risk"), ("MONITOR", "Monitor"), ("NORMAL", "Normal")]
    # MAP_COLORS defined above
    return "".join(f'<span style="display:inline-flex;align-items:center;gap:5px;margin-left:14px;font-size:12px;'
                   f'color:#334155"><span style="width:10px;height:10px;border-radius:99px;background:'
                   f'{MAP_COLORS[l]};border:1.5px solid #0B2545"></span>{t}</span>' for l, t in items)
