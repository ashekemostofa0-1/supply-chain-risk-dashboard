"""
Multimodal U.S. oil, gas & chemical network (sea, rail, road) for the globe.

Nodes are major hubs; edges are well-known corridors with approximate waypoints and
typical transit times. Times are rough planning ranges (no delays, no queueing),
not quotes. find_alternatives() lists every route (up to 3 legs) between two hubs.
"""

NODES = {
    "HOU": {"name": "Houston, TX", "lat": 29.73, "lng": -95.00, "kind": "port"},
    "BMT": {"name": "Port Arthur / Beaumont, TX", "lat": 29.90, "lng": -93.95, "kind": "port"},
    "CRP": {"name": "Corpus Christi, TX", "lat": 27.80, "lng": -97.40, "kind": "port"},
    "MSY": {"name": "New Orleans, LA", "lat": 29.95, "lng": -90.07, "kind": "port"},
    "MID": {"name": "Permian Basin (Midland, TX)", "lat": 32.00, "lng": -102.10, "kind": "inland"},
    "BAK": {"name": "Bakken (Williston, ND)", "lat": 48.15, "lng": -103.60, "kind": "inland"},
    "CHI": {"name": "Chicago, IL", "lat": 41.88, "lng": -87.63, "kind": "inland"},
    "LAX": {"name": "Los Angeles / Long Beach, CA", "lat": 33.75, "lng": -118.20, "kind": "port"},
    "SEA": {"name": "Seattle / Puget Sound, WA", "lat": 47.60, "lng": -122.35, "kind": "port"},
    "NYC": {"name": "New York / New Jersey", "lat": 40.68, "lng": -74.10, "kind": "port"},
    "PHL": {"name": "Philadelphia, PA", "lat": 39.95, "lng": -75.20, "kind": "port"},
    "RTM": {"name": "Rotterdam (Europe)", "lat": 51.95, "lng": 4.10, "kind": "intl"},
    "TYO": {"name": "Tokyo Bay (Northeast Asia)", "lat": 35.30, "lng": 139.80, "kind": "intl"},
    "SSZ": {"name": "Santos (South America)", "lat": -23.95, "lng": -46.30, "kind": "intl"},
    "RTA": {"name": "Ras Tanura (Middle East)", "lat": 26.64, "lng": 50.16, "kind": "intl"},
}

_GULF_TO_FLORIDA = [[27.0, -91.0], [25.0, -86.0], [24.3, -82.0], [24.6, -80.3], [27.0, -79.6]]
_PANAMA = [[22.0, -88.0], [21.5, -86.3], [17.0, -82.0], [12.0, -80.5], [9.35, -79.9], [8.9, -79.5], [7.0, -82.0]]

# (from, to, mode, days_low, days_high, via-signals, waypoints between the two hubs)
EDGES = [
    # ---- road (truck) ----
    ("HOU", "BMT", "road", 0.1, 0.2, [], []),
    ("HOU", "CRP", "road", 0.2, 0.3, [], [[28.8, -96.6]]),
    ("HOU", "MSY", "road", 0.3, 0.5, [], [[30.2, -93.2], [30.45, -91.2]]),
    ("HOU", "MID", "road", 0.5, 0.8, [], [[30.3, -97.7], [31.5, -100.4]]),
    ("HOU", "CHI", "road", 1.5, 2.5, [], [[32.8, -96.8], [34.7, -92.3], [35.1, -90.0], [38.6, -90.2]]),
    ("HOU", "LAX", "road", 2.5, 3.5, [], [[29.4, -98.5], [31.8, -106.4], [32.2, -110.9], [33.4, -112.1]]),
    ("HOU", "NYC", "road", 3.0, 4.0, [], [[30.45, -91.2], [33.5, -86.8], [36.2, -81.7], [39.3, -77.5]]),
    ("CHI", "NYC", "road", 1.5, 2.0, [], [[41.5, -81.7], [40.4, -80.0], [40.3, -76.9]]),
    ("MID", "LAX", "road", 1.5, 2.0, [], [[31.8, -106.4], [32.2, -110.9], [33.4, -112.1]]),
    # ---- rail ----
    ("BAK", "PHL", "rail", 5, 7, [], [[46.9, -96.8], [45.0, -93.3], [41.9, -87.6], [41.5, -81.7], [40.4, -80.0]]),
    ("BAK", "BMT", "rail", 6, 8, [], [[44.4, -100.3], [41.3, -96.0], [39.1, -94.6], [35.5, -97.5], [32.8, -96.8]]),
    ("BAK", "SEA", "rail", 4, 6, [], [[47.5, -111.3], [47.66, -117.4]]),
    ("BAK", "CHI", "rail", 3, 4, [], [[46.9, -96.8], [45.0, -93.3]]),
    ("MID", "HOU", "rail", 1, 2, [], [[31.5, -99.0], [30.3, -97.7]]),
    ("MID", "CRP", "road", 0.4, 0.6, [], [[29.4, -98.5]]),
    ("HOU", "CHI", "rail", 3, 5, [], [[32.5, -93.7], [35.15, -90.05], [38.6, -90.2]]),
    ("HOU", "LAX", "rail", 4, 6, [], [[29.4, -98.5], [31.8, -106.4], [32.2, -110.9], [34.0, -114.5]]),
    ("CHI", "NYC", "rail", 2, 3, [], [[41.5, -81.7], [40.4, -80.0], [40.8, -76.0]]),
    ("CHI", "PHL", "rail", 2, 3, [], [[41.5, -81.7], [40.4, -80.0]]),
    # ---- sea (U.S. coastal and international) ----
    ("HOU", "NYC", "sea", 6, 8, ["weather", "houston"], _GULF_TO_FLORIDA + [[32.0, -77.0], [36.5, -74.5]]),
    ("BMT", "PHL", "sea", 6, 8, ["weather", "port_arthur"], _GULF_TO_FLORIDA + [[32.0, -77.0], [36.5, -74.8], [38.8, -75.0]]),
    ("HOU", "MSY", "sea", 1, 2, ["weather", "houston"], [[28.9, -93.0], [28.9, -90.5]]),
    ("HOU", "RTM", "sea", 15, 18, ["weather", "houston"],
     _GULF_TO_FLORIDA + [[32.0, -75.0], [38.0, -60.0], [43.0, -40.0], [47.0, -20.0], [49.5, -6.0], [51.0, 1.5]]),
    ("BMT", "RTM", "sea", 15, 18, ["weather", "port_arthur"],
     _GULF_TO_FLORIDA + [[32.5, -74.0], [38.5, -58.0], [43.5, -38.0], [47.5, -18.0], [49.8, -5.0], [51.2, 1.6]]),
    ("CRP", "TYO", "sea", 28, 33, ["weather", "panama"],
     [[25.0, -93.0]] + _PANAMA + [[12.0, -100.0], [20.0, -130.0], [28.0, -160.0], [33.0, 170.0], [34.2, 145.0]]),
    ("HOU", "TYO", "sea", 28, 33, ["weather", "houston", "panama"],
     [[27.0, -93.0]] + _PANAMA + [[12.5, -101.0], [20.5, -131.0], [28.5, -161.0], [33.5, 169.0], [34.5, 145.5]]),
    ("LAX", "TYO", "sea", 12, 15, [], [[36.0, -130.0], [40.0, -160.0], [38.0, 170.0], [35.0, 145.0]]),
    ("HOU", "LAX", "sea", 14, 18, ["weather", "houston", "panama"],
     [[27.0, -93.0]] + _PANAMA + [[12.0, -95.0], [18.0, -106.0], [26.0, -114.0]]),
    ("HOU", "SSZ", "sea", 16, 19, ["weather", "houston"],
     [[25.0, -94.0], [22.0, -88.0], [21.3, -86.0], [18.0, -76.0], [13.0, -62.0], [5.0, -45.0], [-2.0, -36.0],
      [-10.0, -34.0], [-20.0, -39.0]]),
    ("RTA", "HOU", "sea", 30, 35, ["hormuz", "bab", "suez", "weather", "houston"],
     [[26.5, 56.5], [22.0, 62.0], [13.0, 51.0], [12.6, 43.4], [20.0, 38.5], [27.5, 34.0], [30.0, 32.5],
      [33.5, 28.0], [36.5, 15.0], [36.0, -5.6], [35.0, -20.0], [30.0, -45.0], [26.0, -70.0], [24.3, -81.0],
      [24.8, -84.5], [27.5, -90.0]]),
    ("RTA", "BMT", "sea", 40, 45, ["hormuz", "good_hope", "weather", "port_arthur"],
     [[26.5, 56.5], [20.0, 62.0], [5.0, 58.0], [-10.0, 50.0], [-25.0, 40.0], [-34.8, 20.0], [-30.0, 8.0],
      [-15.0, -8.0], [3.0, -25.0], [15.0, -50.0], [22.0, -70.0], [24.3, -81.0], [24.8, -84.5], [27.5, -90.0]]),
    ("RTA", "TYO", "sea", 20, 24, ["hormuz", "malacca"],
     [[26.5, 56.5], [22.0, 62.0], [12.0, 72.0], [6.0, 80.0], [5.8, 95.0], [2.5, 101.5], [1.3, 104.0],
      [10.0, 112.0], [22.0, 120.0], [30.0, 128.0]]),
    ("RTA", "RTM", "sea", 20, 24, ["hormuz", "bab", "suez"],
     [[26.5, 56.5], [22.0, 62.0], [13.0, 51.0], [12.6, 43.4], [20.0, 38.5], [27.5, 34.0], [30.0, 32.5],
      [33.5, 28.0], [36.5, 15.0], [36.0, -5.6], [43.0, -10.0], [48.5, -5.5]]),
]

MODE_NAMES = {"sea": "Ship", "rail": "Rail", "road": "Truck"}


def _km(a, b):
    import math
    p1, p2 = math.radians(NODES[a]["lat"]), math.radians(NODES[b]["lat"])
    dl = math.radians(NODES[b]["lng"] - NODES[a]["lng"])
    h = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371 * 2 * math.asin(min(1, math.sqrt(h)))


def _edge_points(e, forward=True):
    a, b, _, _, _, _, mid = e
    pts = [[NODES[a]["lat"], NODES[a]["lng"]]] + mid + [[NODES[b]["lat"], NODES[b]["lng"]]]
    return pts if forward else pts[::-1]


def all_edges():
    """Every corridor, for the default 'all routes' view."""
    return [{"name": f"{NODES[a]['name']} ↔ {NODES[b]['name']}", "mode": m,
             "points": _edge_points(e)} for e in EDGES for a, b, m in [e[:3]]]


def find_alternatives(src: str, dst: str, max_legs: int = 3, limit: int = 8):
    """All simple paths src -> dst (edges usable in both directions), sorted by fastest."""
    adj = {}
    for i, e in enumerate(EDGES):
        adj.setdefault(e[0], []).append((e[1], i, True))
        adj.setdefault(e[1], []).append((e[0], i, False))
    found = []

    def walk(node, seen, legs):
        if node == dst and legs:
            found.append(list(legs))
            return
        if len(legs) >= max_legs:
            return
        for nxt, i, fwd in adj.get(node, []):
            if nxt in seen:
                continue
            if nxt != dst and NODES[nxt]["kind"] == "intl":     # never route through a foreign port
                continue
            legs.append((i, fwd))
            walk(nxt, seen | {nxt}, legs)
            legs.pop()

    walk(src, {src}, [])
    alts = []
    for legs in found:
        stops_ = [src] + [EDGES[i][1] if f else EDGES[i][0] for i, f in legs]
        path_km = sum(_km(x, y) for x, y in zip(stops_, stops_[1:]))
        if path_km > 1.5 * _km(src, dst) + 300:          # skip big geographic detours
            continue
        lo = sum(EDGES[i][3] for i, _ in legs)
        hi = sum(EDGES[i][4] for i, _ in legs)
        modes = [EDGES[i][2] for i, _ in legs]
        stops = [src] + [EDGES[i][1] if f else EDGES[i][0] for i, f in legs]
        signals = sorted({s for i, _ in legs for s in EDGES[i][5]})
        alts.append({"legs": [{"mode": EDGES[i][2], "points": _edge_points(EDGES[i], f)} for i, f in legs],
                     "modes": modes, "stops": stops, "days": (lo, hi), "signals": signals,
                     "label": " → ".join(f"{MODE_NAMES[m]}" for m in modes),
                     "via": " → ".join(NODES[s]["name"].split(" (")[0].split(",")[0] for s in stops)})
    alts.sort(key=lambda a: (a["days"][0], len(a["legs"])))
    if alts:                                   # drop long detours (more than ~2.3x the fastest option)
        best = alts[0]["days"][0]
        alts = [a for a in alts if a["days"][0] <= best * 2.3 + 3]
    return alts[:limit]


def fmt_days(lo, hi):
    if hi < 1:
        return f"{round(lo * 24)}–{round(hi * 24)} hours"
    return f"{lo:g}–{hi:g} days"


def hubs(keys=None):
    keys = keys or list(NODES)
    return [{"name": NODES[k]["name"].split(" (")[0], "lat": NODES[k]["lat"], "lng": NODES[k]["lng"],
             "pulse": k in ("HOU", "BMT")} for k in keys]


def focus_for(points):
    """Camera position that frames a set of [lat, lng] points on the globe."""
    lats = [p[0] for p in points]
    lngs = [p[1] for p in points]
    span = max(max(lats) - min(lats), min(max(lngs) - min(lngs), 360 - (max(lngs) - min(lngs))))
    lng_mid = (max(lngs) + min(lngs)) / 2 if max(lngs) - min(lngs) <= 180 else \
        ((max(lngs) + min(lngs)) / 2 + 180) % 360 - 180
    return {"lat": (max(lats) + min(lats)) / 2, "lng": lng_mid,
            "alt": max(0.55, min(2.4, span / 55 + 0.35))}
